"""
premium.py — ETF 折溢价 / IOPV 估算

两种折溢价来源，按精度优先级：
  A) 接口自带 discount_rate（get_fund_daily 的贴水率）—— 最省事，优先用。
  B) 自算：price vs IOPV。IOPV 有两条路：
       B1) 成分券精算：Σ(成分股收盘价 × quantity) + 现金差额，除以最小申赎单位份数。
       B2) 单位净值代理：用申赎清单的 unit_nav 当净值。
"""
from __future__ import annotations

import math


def _latest(rows, date_key="date"):
    if not rows:
        return None
    return sorted(rows, key=lambda x: str(x.get(date_key, "")))[-1]


def premium_from_interface(fund_daily_rows) -> dict | None:
    """A) Use Pandadata discount_rate ratio; discount is the inverse of premium."""
    last = _latest(fund_daily_rows)
    if not last:
        return None
    dr = last.get("discount_rate")
    close = last.get("close")
    if dr is None:
        return None
    try:
        raw = float(dr)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(raw):
        return None
    premium_bps = -raw * 10_000.0
    return {"source": "interface_discount_rate", "price": close,
            "iopv": None, "premium_bps": round(premium_bps, 2),
            "raw_discount_rate": raw, "discount_rate_unit": "ratio",
            "date": last.get("date")}


def constituents_for_date(rows, data_date) -> list[dict]:
    """Select one basket snapshot and deduplicate components by stock symbol."""
    selected = {}
    for row in rows:
        if str(row.get("date", "")) != str(data_date):
            continue
        code = row.get("stock_symbol")
        if code:
            selected[str(code)] = dict(row)
    return sorted(selected.values(), key=lambda row: str(row.get("stock_symbol", "")))


def iopv_from_constituents(constituent_rows, stock_close_map, cash_component, unit_shares) -> float | None:
    """B1) 成分券精算 IOPV = (Σ 成分股价×quantity + 现金差额) / 最小申赎单位份数。"""
    if not constituent_rows or not unit_shares:
        return None
    basket_value = 0.0
    priced = 0
    for c in constituent_rows:
        code = c.get("stock_symbol")
        qty = c.get("quantity") or 0
        px = stock_close_map.get(code)
        if px is not None and qty:
            basket_value += float(px) * float(qty)
            priced += 1
    if priced == 0:
        return None
    total = basket_value + (cash_component or 0.0)
    return round(total / float(unit_shares), 4)


def premium_from_iopv(price, iopv) -> dict | None:
    """B) 用 IOPV 算折溢价 bps（正=溢价，价格高于净值）。"""
    if not price or not iopv:
        return None
    premium_bps = (float(price) - float(iopv)) / float(iopv) * 1e4
    return {"source": "iopv_estimate", "price": price, "iopv": iopv,
            "premium_bps": round(premium_bps, 2)}


def resolve_premium(fund_daily_rows, cr_row, constituent_rows, stock_close_map,
                    data_date=None) -> dict:
    """综合出折溢价：优先接口贴水率；否则成分精算 IOPV；再否则单位净值代理。"""
    # A) 接口贴水率
    p = premium_from_interface(fund_daily_rows)
    if p is not None:
        return p

    last_daily = _latest(fund_daily_rows)
    price = last_daily.get("close") if last_daily else None

    # B1) 成分精算 IOPV
    selected_constituents = constituents_for_date(
        constituent_rows, data_date
    ) if data_date else constituent_rows
    if cr_row and selected_constituents:
        iopv = iopv_from_constituents(
            selected_constituents, stock_close_map,
            cr_row.get("cash_component"), cr_row.get("unit"))
        if iopv:
            r = premium_from_iopv(price, iopv)
            if r:
                return r

    # B2) 单位净值代理
    if cr_row and price:
        nav = cr_row.get("unit_nav")
        if nav:
            r = premium_from_iopv(price, nav)
            if r:
                r["source"] = "unit_nav_proxy"
                return r

    return {"source": "unavailable", "price": price, "iopv": None,
            "premium_bps": None, "date": data_date}
