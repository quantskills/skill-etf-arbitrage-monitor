#!/usr/bin/env python3
"""run_demo.py — ETF 套利监测离线演示（无需凭证，强制内置样本）。

样本设计：
  - 510300.SH 溢价（价格 4.735 vs 净值~4.712，接口贴水率 -0.49% → 溢价约49bps）→ 触发溢价套利
  - 159919.SZ 折价（贴水率 +0.43%）→ 折价套利
  - 588000.SH 暂停申购（purchase_allowed_flag=0）+ 成交额仅350万 → 演示不可执行/流动性降级
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from etf_arb_report import build_report  # noqa: E402
import formatters                        # noqa: E402

DEMO = ["510300.SH", "159919.SZ", "588000.SH"]


def main():
    report = build_report(DEMO, premium_bps=30, cost_bps=20, min_amount=1000,
                          check_basket=True, prefer="sample")
    print(formatters.to_text(report))
    print("\n" + "-" * 60 + "\nMarkdown 版：\n")
    print(formatters.to_markdown(report))


if __name__ == "__main__":
    main()
