---
name: skill-etf-arbitrage-monitor
description: >
  A-share ETF primary/secondary arbitrage & premium-discount monitor. Use when
  a user wants to track ETF IOPV vs market price gaps, creation/redemption
  basket feasibility, and premium/discount driven arbitrage windows. Pulls ETF
  creation-redemption lists, constituent baskets, and NAV, computes real-time
  premium/discount and cash-difference, and flags actionable arbitrage signals.
license: GPL-3.0-only
category: 工具
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-etf-arbitrage-monitor
  repository_url: https://github.com/quantskills/skill-etf-arbitrage-monitor
  project_type: skill
  collection: etf-analytics
  status: community-draft
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "粘贴 ETF 代码（如 510300.SH, 159919.SZ），或上传自选 ETF 列表；说明关注的溢价阈值",
    "required": true
  },
  "fields": [
    {
      "key": "premium_threshold_bps",
      "label": "溢价/折价触发阈值（bps）",
      "type": "number",
      "default": "30",
      "help": "价格相对 IOPV 偏离超过该值即视为潜在套利窗口"
    },
    {
      "key": "min_amount",
      "label": "最低成交额过滤（万元）",
      "type": "number",
      "default": "1000",
      "help": "过滤流动性过低、套利难成交的 ETF"
    },
    {
      "key": "check_basket",
      "label": "是否核算申赎篮子可行性",
      "type": "select",
      "default": "yes",
      "options": [
        { "value": "yes", "label": "是（拉成分篮子+现金差额）" },
        { "value": "no", "label": "否（仅价差监控）" }
      ]
    }
  ],
  "prompt_template": "{{#task}}ETF 与要求：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}对上述 ETF 做一二级市场套利与折溢价监控。{{#premium_threshold_bps}}溢价/折价触发阈值 {{premium_threshold_bps}} bps。{{/premium_threshold_bps}}{{#min_amount}}过滤成交额低于 {{min_amount}} 万元的标的。{{/min_amount}}{{#check_basket}}篮子可行性核算：{{check_basket}}。{{/check_basket}}计算 IOPV 估算净值、价格相对净值的折溢价、申赎清单现金差额与最小申赎单位约束，标记可套利窗口与方向（溢价→申购卖出 / 折价→买入赎回），输出中文信号清单并标注数据降级项。仅研究参考，不构成投资建议。"
}
```

# skill-etf-arbitrage-monitor

role: skill · output: ETFArbReport (JSON + text) · paradigm: ETF premium/discount arbitrage scan

把"这只 ETF 现在贵了还是便宜了、能不能一二级套利"变成可计算、可分级的信号。这是组织里 **完全空白** 的 ETF 赛道的第一个技能。

## 🎯 这个 Skill 解决什么问题

组织 118 仓里 **ETF 相关技能为零**。而 ETF 一二级套利(溢价申购卖出 / 折价买入赎回)是 A 股最经典的低风险套利之一,关键在于实时算清 **IOPV(基金份额参考净值) vs 二级市场价格** 的偏离、以及申赎篮子的现金差额与最小申赎单位约束。散户/机构都需要一个能盯一篮子 ETF、自动标出套利窗口的工具。

本 Skill 计算三层信号:

- **折溢价**:二级价格相对 IOPV/单位净值的偏离(bps),正=溢价、负=折价。
- **篮子可行性**:申赎清单(成分股+现金替代+现金差额)是否可实际组建,最小申赎单位(如 90 万份)约束。
- **套利方向与毛收益**:溢价→申购(买成分)再二级卖出;折价→二级买入再赎回(拿成分)。扣双边成本后是否为正。

## ⚡ 工作流（Agent 按此执行）

1. **解析 ETF 池**:提取 ETF 代码,标准化。
2. **拉数据**:`scripts/data_source.py` 取 `get_fund_etf_cr`(申赎清单、单位净值、申赎开关)、`get_fund_etf_constituents`(成分篮子)、ETF 二级行情(`get_fund_daily`)；所有关键数据对齐到同一交易日。
3. **算折溢价**:`scripts/premium.py`,IOPV 估算(成分实时价加权)或用最近净值代理,算价格偏离 bps。
4. **核篮子**:`scripts/basket.py`,现金差额 + 最小申赎单位 + 成分停牌剔除,判断可行性。
5. **出信号**:`scripts/etf_arb_report.py` → `ETFArbReport`,按偏离绝对值降序,标方向+扣费后毛收益,过滤流动性不足。
6. **解释**:指出哪只、溢价还是折价、方向、约束(如最小申赎单位太大)。

```bash
python scripts/etf_arb_report.py --symbols 510300.SH,159919.SZ --premium-bps 30 --out report.json
python examples/run_demo.py   # 无凭证回退样本
```

## 🗃️ 输入契约

| 输入 | 形态 | 必需 | 说明 |
|------|------|------|------|
| `symbols` | 逗号分隔 / CSV | 是 | ETF 代码 |
| `premium_threshold_bps` | float | 否 | 默认 30 |
| `min_amount` | float | 否 | 默认 1000(万元),流动性过滤 |
| `check_basket` | yes/no | 否 | 默认 yes |

输出 `ETFArbReport`:`status / items[] (symbol, iopv, price, premium_bps, direction, feasible, actionable, gross_bps, data_date, sources, constraints[]) / degraded[]`。`get_fund_daily.discount_rate` 按小数比例换算为 bps（`0.003 = 30bps`）；申赎清单、成交额、同日篮子任一缺失时必须 fail closed，不给可执行结论。

## 📦 输出契约

产物对象 `ETFArbReport`（JSON + 中文文本）：

| 字段 | 说明 |
|------|------|
| `items[]` | 每标的：`symbol, iopv, price, premium_bps, direction(申购/赎回), feasible, gross_bps, constraints[]` |
| `degraded[]` | 降级项（申赎通道关闭/流动性不足/数据缺失） |

文件产物：`--out report.json`、`--md report.md`。折溢价与可行性须标注数据日期与来源接口（`get_fund_etf_cr` / `get_fund_daily`），暂停申赎须显式标 `feasible=false`。

## 🔗 管线定位

```
ETF 池 → [本 Skill：折溢价+篮子可行性] → 套利执行判断
```
它是 ETF 交易的**信号前置**,组织此前没有任何 ETF 工具,填补空白。

## 📦 仓库结构

```
skill-etf-arbitrage-monitor/
├── SKILL.md / README.md / requirements.txt / .gitignore
├── scripts/ data_source.py · premium.py · basket.py · etf_arb_report.py · formatters.py
├── references/ methodology.md(IOPV估算+套利机制) · data-fields.md
└── examples/ run_demo.py · sample_data/ · sample_report.md
```

## ✅ 质量门槛

产物交付前须满足（不达标则降级并在报告显式声明，不静默通过）：

- **可溯源**：每个关键数字可回溯到具体 Pandadata 接口 + 数据日期；缺失数据进 `degraded[]`，绝不编造或用近似冒充真实值。
- **降级透明**：任一数据源为空/受限时，报告如实标注并降低结论置信度。
- **口径一致**：单位、频率、基准口径在报告中显式声明。
- **仅研究**：产物为研究/教育参考，不构成投资建议，不承诺收益。
- 申赎通道关闭（purchase/redemption_allowed_flag=0）时套利单边须标 feasible=false，不给可执行结论。

## ⚠️ 使用规则

- **接口字段已实测确认(2026-07-27,MCP get_method_doc)**:
  - `get_fund_etf_cr` ✅ 实测字段:`cash_component`(现金差额)、`estimated_cash_component`(预估现金差额)、`unit`(最小申赎单位份数)、`creation_unit`(单位净值资产)、`cash_substitution_rate`(现金替代比例上限%)、`unit_nav`(单位净值)、`purchase_allowed_flag`/`redemption_allowed_flag`(申赎开关)、`index_symbol`(挂钩指数)。**比原设计更全**——申赎开关可直接判断套利通道是否开放。
  - `get_fund_etf_cr` / `get_fund_etf_constituents` ✅ 申赎清单含 `unit_nav/index_symbol`，成分篮子经 constituents 展开。
- IOPV 为成分加权估算,盘中无 tick 时用分钟线代理,报告须声明精度。
- 申赎有 T+0/T+1 规则差异(跨境、货币、商品 ETF 不同),须按 ETF 类型区分。`purchase_allowed_flag=0` 或 `redemption_allowed_flag=0` 时套利单边不可行,须先过滤。
- 只做研究/套利可行性参考,不构成投资建议。
