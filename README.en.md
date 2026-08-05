# ETF Arbitrage Monitor

[Chinese README](README.md) | English

This skill scans A-share ETFs for primary/secondary-market premium and discount
conditions. It estimates IOPV, checks the creation/redemption basket, applies liquidity
and cost gates, and emits a structured monitor report.

## Quick start

```bash
pip install -r requirements.txt
python examples/run_demo.py
python scripts/etf_arb_report.py --symbols 510300.SH,159919.SZ,588000.SH \
  --premium-bps 30 --cost-bps 20 --min-amount 1000 \
  --out report.json --md report.md
```

The offline demo uses bundled samples. A live-data run can use the Pandadata SDK via
the adapter. The monitor fails closed when a required basket, permission flag, price,
or liquidity field is missing.

## Decision fields

The report includes the price-to-NAV gap, estimated IOPV, cash component, creation unit,
purchase/redemption permissions, cost assumptions, direction label, and degradation
reasons. Key sources are `get_fund_etf_cr`, `get_fund_etf_constituents`, `get_fund_daily`,
and `get_stock_daily`.

## Research boundary

IOPV and cost estimates are approximations and fund rules can change. Data is not real
time. Outputs are for research and education only; the project does not place orders and
is not investment advice. Confirm current fund documents before any operational use.

## License

GPL-3.0-only. See [LICENSE](LICENSE).
