"""事情の割合の表: 事象の馬（崩れた人気馬・来た穴馬）と母集団（同じ帯の馬全体）で、各事情の割合を並べて比べる。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .runner_circumstances import CIRCUMSTANCES

COLUMNS: tuple[str, ...] = ("事情", "事象の頭数", "事象での割合", "母集団の頭数", "母集団での割合", "倍率", "意味")


@dataclass(frozen=True)
class CircumstanceShareTable:
    """``event``（事象が起きた馬の行）と ``base``（母集団の行）の、``CIRCUMSTANCES`` の列ごとの割合と倍率（事象 ÷ 母集団）。

    倍率が 1 より大きい事情は、事象の馬に多い（人気馬が崩れる・穴馬が来る、の手がかりの候補）。倍率の大きい順に並べる。
    """

    def build(self, event: pd.DataFrame, base: pd.DataFrame, *, title: str, note: str = "") -> Table:
        rows = [self._row(name, meaning, event, base) for name, meaning in CIRCUMSTANCES.items()]
        rows.sort(key=lambda row: -(row["倍率"] if row["倍率"] == row["倍率"] else -1))
        return Table.from_records(rows, COLUMNS, title=title, note=note)

    def _row(self, name: str, meaning: str, event: pd.DataFrame, base: pd.DataFrame) -> dict:
        event_share = float(event[name].mean()) if len(event) else float("nan")
        base_share = float(base[name].mean()) if len(base) else float("nan")
        ratio = event_share / base_share if base_share else float("nan")
        return {
            "事情": name, "事象の頭数": int(event[name].sum()), "事象での割合": _percent(event_share),
            "母集団の頭数": int(base[name].sum()), "母集団での割合": _percent(base_share),
            "倍率": round(ratio, 2) if ratio == ratio else float("nan"), "意味": meaning,
        }


def _percent(value: float) -> str:
    return "—" if value != value else f"{value:.1%}"
