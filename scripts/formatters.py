"""formatters.py — ETFArbReport 渲染 JSON / 中文文本 / Markdown"""
from __future__ import annotations
import json


def to_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def _sig(it):
    p = it.get("premium_bps")
    if p is None:
        return "—"
    return f"+{p:.1f}(溢价)" if p > 0 else f"{p:.1f}(折价)"


def to_text(report: dict) -> str:
    L = []
    L.append("=" * 60)
    L.append("A股 ETF 一二级套利 / 折溢价监控")
    L.append(f"生成时间: {report['generated_at']}   ETF 数: {report['universe_size']}   后端: {report['backend']}")
    L.append(f"溢价触发阈值: {report['params']['premium_threshold_bps']} bps   成本估计: {report['params']['cost_bps']} bps")
    L.append("=" * 60)
    if not report["items"]:
        L.append("（在给定阈值下无可套利窗口）")
    for it in report["items"]:
        flag = "🔴" if it.get("actionable") else "  "
        L.append("")
        L.append(f"{flag} {it['symbol']} {it.get('name','')}   折溢价 {_sig(it)}   来源[{it.get('premium_source')}]")
        d = it.get("arb", {})
        L.append(f"    方向: {d.get('direction','—')}   可执行: {'是' if it.get('actionable') else '否'}"
                 + (f"（{d.get('note')}）" if d.get('note') else ""))
        g = it.get("gross_bps")
        if g is not None:
            L.append(f"    扣费后毛收益: {g:+.1f} bps")
        for c in it.get("constraints", []):
            L.append(f"    · {c}")
    if report.get("degraded"):
        L.append("")
        L.append("⚠️ 数据降级:")
        for s in report["degraded"]:
            L.append(f"    - {s}")
    L.append("")
    L.append("免责声明：折溢价/IOPV 为估算，申赎规则以基金公告为准。仅供研究参考，不构成投资建议。")
    return "\n".join(L)


def to_markdown(report: dict) -> str:
    L = [f"# ETF 套利监控 — {report['generated_at']}", ""]
    L.append(f"ETF {report['universe_size']} 只 · 后端 `{report['backend']}` · 阈值 {report['params']['premium_threshold_bps']}bps")
    L.append("")
    L.append("| 代码 | 名称 | 折溢价 | 方向 | 可执行 | 毛收益bps |")
    L.append("|---|---|---|---|---|---|")
    for it in report["items"]:
        d = it.get("arb", {})
        L.append(f"| {it['symbol']} | {it.get('name','')} | {_sig(it)} | {d.get('direction','—')} | "
                 f"{'✅' if it.get('actionable') else '❌'} | {it.get('gross_bps','—')} |")
    L.append("")
    L.append("> 折溢价/IOPV 为估算。仅供研究参考，不构成投资建议。")
    return "\n".join(L)
