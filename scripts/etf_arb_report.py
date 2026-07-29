#!/usr/bin/env python3
"""
etf_arb_report.py — ETF 套利监测 CLI 入口

用法:
  python scripts/etf_arb_report.py --symbols 510300.SH,159919.SZ \
      --premium-bps 30 --cost-bps 20 --min-amount 1000 \
      --out report.json --md report.md

无凭证自动回退内置样本（examples/sample_data/）。
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_source import DataSource   # noqa: E402
import premium as prem               # noqa: E402
import basket as bkt                 # noqa: E402
import formatters                    # noqa: E402


def parse_symbols(raw: str) -> list[str]:
    if Path(raw).exists():
        text = Path(raw).read_text(encoding="utf-8")
        toks = [t.strip() for line in text.splitlines() for t in line.replace(",", " ").split()]
    else:
        toks = [t.strip() for t in raw.replace(",", " ").split()]
    return [t.upper() for t in toks if t and t[0].isdigit()]


def build_report(symbols, premium_bps, cost_bps, min_amount, check_basket=True,
                 prefer=None, data_source=None) -> dict:
    ds = data_source or DataSource(prefer=prefer)
    today = datetime.now()
    d_end = today.strftime("%Y%m%d")
    d_start = (today - timedelta(days=15)).strftime("%Y%m%d")

    degraded = set()
    items = []
    for sym in symbols:
        cr_rows = ds.etf_cr(sym, d_start, d_end)
        daily_rows = ds.fund_daily(sym, d_start, d_end)
        last_daily = sorted(daily_rows, key=lambda x: str(x.get("date", "")))[-1] if daily_rows else {}
        data_date = last_daily.get("date")
        cr_row = next((row for row in cr_rows
                       if str(row.get("date", "")) == str(data_date)), None)

        constituent_rows = []
        stock_close_map = {}
        if check_basket:
            all_constituents = ds.etf_constituents(sym, d_start, d_end)
            constituent_rows = prem.constituents_for_date(all_constituents, data_date)
            # 只在需要成分精算 IOPV 时（接口无 discount_rate）才拉成分股价
            need_iopv = not (daily_rows and any(r.get("discount_rate") is not None for r in daily_rows))
            if need_iopv and constituent_rows:
                codes = [c.get("stock_symbol") for c in constituent_rows if c.get("stock_symbol")]
                if codes:
                    sd = ds.stock_daily(codes, d_start, d_end)
                    for r in sorted(sd, key=lambda row: str(row.get("date", ""))):
                        if data_date and str(r.get("date", "")) <= str(data_date):
                            stock_close_map[r.get("symbol")] = r.get("close")

        if not cr_row:
            degraded.add(f"{sym}: 缺少与行情同日的 ETF 申赎清单")
        if not daily_rows:
            degraded.add(f"{sym}: 无 ETF 申赎清单/行情数据")

        p = prem.resolve_premium(
            daily_rows, cr_row, constituent_rows, stock_close_map, data_date=data_date
        )
        premium_val = p.get("premium_bps")

        # 流动性过滤
        amount = last_daily.get("amount")
        amt_wan = float(amount) / 1e4 if amount is not None else None
        if amt_wan is None:
            degraded.add(f"{sym}: 成交额缺失，不能判断流动性")
        elif amt_wan < min_amount:
            degraded.add(f"{sym}: 成交额 {amt_wan:.0f}万 < 阈值 {min_amount}万，流动性不足已降级")

        feas = bkt.basket_feasibility(
            cr_row, constituent_rows, require_constituents=check_basket
        )
        if not feas["feasible"]:
            degraded.add(f"{sym}: " + "；".join(feas["constraints"]))
        arb = bkt.arb_direction(premium_val, cr_row)
        gross = bkt.net_gross_bps(premium_val, cost_bps)

        actionable = (premium_val is not None
                      and abs(premium_val) >= premium_bps
                      and arb.get("executable")
                      and feas["feasible"]
                      and (gross is not None and gross > 0)
                      and (amt_wan is not None and amt_wan >= min_amount))

        name = cr_row.get("name") if cr_row else (last_daily.get("name") if last_daily else "")
        items.append({
            "symbol": sym, "name": name or "",
            "iopv": p.get("iopv"), "price": p.get("price"),
            "premium_bps": premium_val, "premium_source": p.get("source"),
            "direction": arb.get("direction"), "arb": arb, "gross_bps": gross,
            "feasible": bool(feas["feasible"]),
            "data_date": data_date,
            "sources": {
                "premium": p.get("source"),
                "price": "get_fund_daily" if last_daily else None,
                "basket": "get_fund_etf_constituents" if constituent_rows else None,
                "creation_redemption": "get_fund_etf_cr" if cr_row else None,
            },
            "constraints": feas["constraints"],
            "actionable": bool(actionable),
        })

    # 可套利的排前，再按折溢价绝对值降序
    items.sort(key=lambda x: (x["actionable"], abs(x["premium_bps"]) if x["premium_bps"] is not None else -1),
               reverse=True)

    complete = [
        item for item in items
        if item["premium_bps"] is not None
        and item["price"] is not None
        and item["feasible"]
        and item["data_date"]
    ]
    status = "ok" if len(complete) == len(items) else "degraded" if complete else "failed"
    degraded_list = sorted(degraded)
    return {
        "status": status,
        "generated_at": today.strftime("%Y-%m-%d %H:%M"),
        "backend": ds.backend,
        "universe_size": len(symbols),
        "params": {"premium_threshold_bps": premium_bps, "cost_bps": cost_bps, "min_amount": min_amount},
        "items": items,
        "degraded": degraded_list,
        "degraded_sources": degraded_list,
    }


def main():
    ap = argparse.ArgumentParser(description="A股 ETF 一二级套利/折溢价监测")
    ap.add_argument("--symbols", required=True, help="逗号分隔 ETF 代码，或 CSV 路径")
    ap.add_argument("--premium-bps", type=float, default=30.0)
    ap.add_argument("--cost-bps", type=float, default=20.0)
    ap.add_argument("--min-amount", type=float, default=1000.0, help="最低成交额(万元)")
    ap.add_argument("--no-basket", action="store_true", help="不核算篮子可行性")
    ap.add_argument("--prefer", choices=["sdk", "sample"], default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    symbols = parse_symbols(args.symbols)
    if not symbols:
        print("未解析到有效 ETF 代码", file=sys.stderr)
        sys.exit(2)

    report = build_report(symbols, args.premium_bps, args.cost_bps, args.min_amount,
                          check_basket=not args.no_basket, prefer=args.prefer)
    print(formatters.to_text(report))
    if args.out:
        Path(args.out).write_text(formatters.to_json(report), encoding="utf-8")
        print(f"\n[已写出 JSON] {args.out}")
    if args.md:
        Path(args.md).write_text(formatters.to_markdown(report), encoding="utf-8")
        print(f"[已写出 Markdown] {args.md}")
    return 2 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
