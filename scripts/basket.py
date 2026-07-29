"""
basket.py — 申赎篮子可行性与套利方向判定
"""
from __future__ import annotations


def _latest(rows, date_key="date"):
    if not rows:
        return None
    return sorted(rows, key=lambda x: str(x.get(date_key, "")))[-1]


# 现金替代标志：1允许 2必须 3禁止 4退补
FLAG_CN = {1: "允许现金替代", 2: "必须现金替代", 3: "禁止现金替代", 4: "退补现金替代"}


def basket_feasibility(cr_row, constituent_rows, require_constituents=True) -> dict:
    """判断申赎篮子是否可实际组建，返回约束清单。"""
    constraints = []
    feasible = True

    if not cr_row:
        return {"feasible": False, "constraints": ["无申赎清单数据"], "unit": None}
    if require_constituents and not constituent_rows:
        return {"feasible": False, "constraints": ["无同日成分券数据"], "unit": cr_row.get("unit")}

    # 申赎开关
    if cr_row.get("purchase_allowed_flag") == 0:
        constraints.append("暂停申购（溢价套利单边不可行）")
    if cr_row.get("redemption_allowed_flag") == 0:
        constraints.append("暂停赎回（折价套利单边不可行）")

    unit = cr_row.get("unit")
    if unit:
        constraints.append(f"最小申赎单位 {unit:,} 份")
    creation = cr_row.get("creation_unit")
    if creation:
        constraints.append(f"单位申赎门槛约 {creation:,.0f} 元")

    # 现金差额
    cc = cr_row.get("cash_component")
    if cc is not None:
        constraints.append(f"现金差额 {cc:,.0f} 元")

    # 成分中"禁止现金替代且停牌"会阻断篮子——这里只标记必须现金替代的比例
    if constituent_rows:
        missing_flags = sum(1 for c in constituent_rows
                            if c.get("cash_substitution_flag") is None)
        must_cash = sum(1 for c in constituent_rows if c.get("cash_substitution_flag") == 2)
        forbid_cash = sum(1 for c in constituent_rows if c.get("cash_substitution_flag") == 3)
        blocked = sum(
            1 for c in constituent_rows
            if c.get("cash_substitution_flag") == 3
            and c.get("suspend_flag") in (1, True, "1")
        )
        total = len(constituent_rows)
        if total:
            constraints.append(f"成分 {total} 只（必须现金替代 {must_cash}，禁止现金替代 {forbid_cash}）")
        if missing_flags:
            feasible = False
            constraints.append(f"{missing_flags} 只成分缺现金替代标志")
        if blocked:
            feasible = False
            constraints.append(f"{blocked} 只停牌且禁止现金替代，篮子不可组建")

    return {"feasible": feasible, "constraints": constraints, "unit": unit}


def arb_direction(premium_bps, cr_row) -> dict:
    """根据折溢价方向+申赎开关，给出套利方向与是否可执行。"""
    if premium_bps is None:
        return {"direction": "无", "executable": False, "note": "折溢价数据缺失"}

    purchase_ok = (cr_row or {}).get("purchase_allowed_flag") == 1
    redeem_ok = (cr_row or {}).get("redemption_allowed_flag") == 1

    if premium_bps > 0:
        # 溢价：申购(买成分/现金申购)→ 二级卖出
        return {"direction": "溢价套利：申购→二级卖出", "executable": purchase_ok,
                "note": "" if purchase_ok else "申购暂停，不可执行"}
    else:
        # 折价：二级买入 → 赎回(拿成分卖出)
        return {"direction": "折价套利：二级买入→赎回", "executable": redeem_ok,
                "note": "" if redeem_ok else "赎回暂停，不可执行"}


def net_gross_bps(premium_bps, cost_bps=20.0) -> float | None:
    """扣双边成本后的毛收益 bps（成本默认 20bps：佣金+冲击+成分买卖价差的粗估）。"""
    if premium_bps is None:
        return None
    return round(abs(premium_bps) - cost_bps, 2)
