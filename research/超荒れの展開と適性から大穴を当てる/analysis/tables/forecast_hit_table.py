"""展開の予想（前日の時点のペースの確率）が、実際のペースをどれだけ当てていたかを、決着の分け方ごとに並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..theory.race_table import MULTI, OTHER, WIN_ONLY
from .cells import percent
from .pace_share_table import PACES

_NOTE = ("予想のペース = 予想「展開から着順を予想」③ の前日の時点の確率がいちばん大きい区分（その年より前だけで学んだ年ごとの予測。2016年から）。"
         "「予想どおり」は結果のペースが予想と同じ、「予想より速い」は予想より速い区分になったレース。")


@dataclass(frozen=True)
class ForecastHitTable:
    """``summary`` は決着ごとの当たり方、``matrix`` は決着 × 予想のペース ごとの結果のペースの割合。"""

    def summary(self, races: pd.DataFrame, title: str) -> Table:
        known = self._known(races)
        rows = [self._summary_row(outcome, known.loc[known["outcome"] == outcome]) for outcome in (MULTI, WIN_ONLY, OTHER)]
        rows.append(self._summary_row("（全レース）", known))
        columns = ["決着", "予想のあるレース数", "予想どおり", "予想より速い", "予想より遅い", "ハイ予想のうちハイになった", "スロー予想のうちスローになった"]
        return Table(columns, rows, title=title, note=_NOTE)

    def matrix(self, races: pd.DataFrame, title: str) -> Table:
        known = self._known(races)
        rows = []
        for outcome in (MULTI, WIN_ONLY, OTHER, "（全レース）"):
            part = known if outcome == "（全レース）" else known.loc[known["outcome"] == outcome]
            for forecast in PACES:
                cell = part.loc[part["forecast_pace"] == forecast]
                rows.append([outcome, forecast, len(cell), *[percent((cell["pace"] == pace).sum(), len(cell)) for pace in PACES]])
        columns = ["決着", "予想のペース", "レース数", *[f"結果が{pace}" for pace in PACES]]
        return Table(columns, rows, title=title, note=_NOTE)

    @staticmethod
    def _known(races: pd.DataFrame) -> pd.DataFrame:
        return races.loc[races["pace"].isin(PACES) & races["forecast_pace"].notna()]

    @staticmethod
    def _summary_row(label: str, part: pd.DataFrame) -> list[object]:
        n = len(part)
        high = part.loc[part["forecast_pace"] == "ハイ"]
        slow = part.loc[part["forecast_pace"] == "スロー"]
        return [label, n, *[percent((part["pace_vs_forecast"] == kind).sum(), n) for kind in ("予想どおり", "予想より速い", "予想より遅い")],
                percent((high["pace"] == "ハイ").sum(), len(high)), percent((slow["pace"] == "スロー").sum(), len(slow))]
