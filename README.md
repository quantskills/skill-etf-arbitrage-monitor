# skill-etf-arbitrage-monitor

[English](README.en.md)

A股 ETF 一二级市场套利 / 折溢价监控 —— 扫描一篮子 ETF，计算 **IOPV/净值 vs 二级价格的折溢价**、**申赎篮子可行性**（现金差额、最小申赎单位、申赎开关）、**套利方向与扣费后毛收益**，标出真正可执行的套利窗口。

> QuantSkills 组织技能 · 数据源 Pandadata · 组织首个 ETF 方向技能 · 仅供研究参考，不构成投资建议。

## 快速开始

```bash
pip install -r requirements.txt   # 纯标准库，无强制依赖

# 离线演示（无需凭证，内置样本）
python examples/run_demo.py

# 真实扫描（需 panda_data SDK，见 skill-pandadata-api）
python scripts/etf_arb_report.py --symbols 510300.SH,159919.SZ,588000.SH \
    --premium-bps 30 --cost-bps 20 --min-amount 1000 \
    --out report.json --md report.md
```

## 折溢价三级数据源（按精度优先）

`scripts/premium.py` 自动择优：

1. **接口贴水率**（`get_fund_daily.discount_rate`）—— 按小数比例换算，`0.003 = 30bps`；原始值与单位写入 JSON 追踪。
2. **成分精算 IOPV**（`get_fund_etf_constituents` 的 `stock_symbol`+`quantity` × 成分股收盘价 + 现金差额 ÷ 最小申赎单位）。
3. **单位净值代理**（申赎清单 `unit_nav`）。

## 套利判定逻辑

- **溢价**（价格 > 净值）→ 申购（组建成分/现金申购）→ 二级卖出；需 `purchase_allowed_flag=1`。
- **折价**（价格 < 净值）→ 二级买入 → 赎回（拿成分卖出）；需 `redemption_allowed_flag=1`。
- **可执行(actionable)** 需同时满足：折溢价 ≥ 阈值、同日申赎清单与篮子完整、申赎通道开放、扣费后毛收益 > 0、成交额存在且流动性达标。任一关键数据缺失均 fail closed。

这是本技能的核心价值：**过滤掉"看着能套利、实际做不了"的陷阱**（申购暂停 / 单位门槛太高 / 流动性不足）。

## 接口字段（2026-07-27 实测确认）

| 接口 | 关键字段 |
|---|---|
| `get_fund_etf_cr` | cash_component, unit, creation_unit, unit_nav, purchase/redemption_allowed_flag, index_symbol |
| `get_fund_daily` | close, amount, **discount_rate（贴水率，小数比例）** |
| `get_fund_etf_constituents` | stock_symbol, quantity, cash_substitution_flag |

## 目录

```
scripts/     data_source.py · premium.py · basket.py · etf_arb_report.py · formatters.py
references/  methodology.md · data-fields.md
examples/    run_demo.py · sample_data/ · sample_report.md
```

## 免责

折溢价/IOPV 为估算，申赎规则与费率以基金公告为准。数据非实时。仅供研究，不构成投资建议。

## 许可证

GPL-3.0-only，详见 [LICENSE](LICENSE)。
