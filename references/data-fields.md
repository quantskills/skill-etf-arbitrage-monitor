# 数据字段映射 (data-fields) — 2026-07-27 实测确认

## get_fund_etf_cr（ETF 申赎清单）
| 字段 | 含义 | 用途 |
|---|---|---|
| cash_component | 现金差额(元) | IOPV 精算 + 篮子成本 |
| estimated_cash_component | 预估现金差额 | 盘中估算 |
| unit | 最小申赎单位(份) | IOPV 分母 + 门槛 |
| creation_unit | 单位申赎资产净值(元) | 资金门槛展示 |
| unit_nav | 单位净值 | IOPV 代理(降级) |
| cash_substitution_rate | 现金替代比例上限(%) | 篮子约束 |
| purchase_allowed_flag | 是否允许申购(1/0) | 溢价套利前置 |
| redemption_allowed_flag | 是否允许赎回(1/0) | 折价套利前置 |
| index_symbol | 挂钩指数 | 标的识别 |

## get_fund_daily（ETF 二级行情）
| 字段 | 含义 | 用途 |
|---|---|---|
| close | 收盘价 | 折溢价分子 |
| amount | 成交额 | 流动性过滤 |
| **discount_rate** | **贴水率(%)** | **折溢价首选来源(接口直接给)** |
| discount | 贴水(绝对) | 辅助 |

## get_fund_etf_constituents（申赎清单成分券）
| 字段 | 含义 | 用途 |
|---|---|---|
| stock_symbol | 成分股代码 | IOPV 精算取价 |
| quantity | 成分股数量(股) | IOPV 权重 |
| cash_substitution_flag | 现金替代标志(1允许/2必须/3禁止/4退补) | 篮子可行性 |
| cash_premium_rate / cash_discount_rate | 现金替代溢/折价比例 | 篮子成本细化 |

## get_stock_daily（成分股收盘价，仅在接口无 discount_rate 时才需）
| close | 成分股收盘价 | IOPV 精算 |

## 注意
- 网关模式返回行数受套餐配额限制，大 ETF 池需分批。
- 货币 ETF（如 159001）成分为特殊标的，折溢价套利不适用，应过滤。
- 日期统一 YYYYMMDD。
