"""
data_source.py — Pandadata 适配层（ETF 套利监测）

三层回退：
  1) 生产：import panda_data SDK 直连（组织标准）。
  2) 无 SDK：回退 examples/sample_data/*.json 内置样本，保证离线可跑。
  3) --prefer sample 强制样本。

接口日期格式 YYYYMMDD；symbol 传 "" 或省略表示全市场。
SDK 返回可能是 DataFrame / list[dict] / {"result":[...]}，统一成 list[dict]。
"""
from __future__ import annotations
import json
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "sample_data"


def _sdk_available() -> bool:
    try:
        import panda_data  # noqa: F401
        return True
    except Exception:
        return False


def _call_sdk(method: str, **params) -> list[dict]:
    import panda_data
    fn = getattr(panda_data, method)
    res = fn(**params)
    try:
        import pandas as pd
        if isinstance(res, pd.DataFrame):
            return res.to_dict("records")
    except Exception:
        pass
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        # gateway dataframe 形态: {"type":"dataframe","columns":[...],"rows":[[...]]}
        r = res.get("result", res)
        if isinstance(r, dict) and r.get("type") == "dataframe":
            cols = r.get("columns", [])
            return [dict(zip(cols, row)) for row in r.get("rows", [])]
        if isinstance(r, list):
            return r
    return []


def _call_sample(method: str, **params) -> list[dict]:
    f = SAMPLE_DIR / f"{method}.json"
    if not f.exists():
        return []
    rows = json.loads(f.read_text(encoding="utf-8"))
    symbol = params.get("symbol")
    if symbol and rows and "symbol" in rows[0]:
        syms = [symbol] if isinstance(symbol, str) else list(symbol)
        rows = [r for r in rows if r.get("symbol") in syms]
    return rows


class DataSource:
    def __init__(self, prefer: str | None = None):
        if prefer == "sample":
            self.backend = "sample"
        elif prefer == "sdk" or _sdk_available():
            self.backend = "sdk"
        elif SAMPLE_DIR.exists():
            self.backend = "sample"
        else:
            self.backend = "none"

    def fetch(self, method: str, **params) -> list[dict]:
        if self.backend == "sdk":
            try:
                return _call_sdk(method, **params)
            except Exception as e:  # noqa: BLE001
                print(f"[data_source] SDK {method} failed: {e}")
                return []
        if self.backend == "sample":
            return _call_sample(method, **params)
        return []

    # --- ETF 语义化封装 ---
    def etf_cr(self, symbol, start, end):
        """申赎清单：现金差额/最小申赎单位/申赎开关/单位净值。"""
        return self.fetch("get_fund_etf_cr", symbol=symbol, start_date=start, end_date=end)

    def etf_constituents(self, symbol, start, end):
        """申赎清单成分券：stock_symbol + quantity（IOPV 精算用）。"""
        return self.fetch("get_fund_etf_constituents", symbol=symbol, start_date=start, end_date=end)

    def fund_daily(self, symbol, start, end):
        """ETF 二级行情：close/amount + 接口自带 discount_rate（贴水率）。

        注意（2026-07-27 实测）：get_fund_daily 在 gateway 模式偶发
        'Unable to serialize NAType'（含空值列的 pandas 序列化 bug，网关侧）。
        首次失败时用 fields 只取核心字段重试，规避含 NA 的列；仍失败则由
        fetch 兜底返回 []，上层用 discount_rate 缺失→IOPV 自算路径降级。
        """
        rows = self.fetch("get_fund_daily", symbol=symbol, start_date=start, end_date=end)
        if rows:
            return rows
        # NAType 序列化失败重试：只取核心字段
        return self.fetch("get_fund_daily", symbol=symbol, start_date=start, end_date=end,
                          fields=["symbol", "date", "close", "discount", "discount_rate", "amount"])

    def stock_daily(self, symbols, start, end):
        """成分股收盘价（IOPV 精算用；symbols 可为列表）。"""
        return self.fetch("get_stock_daily", symbol=symbols, start_date=start, end_date=end)
