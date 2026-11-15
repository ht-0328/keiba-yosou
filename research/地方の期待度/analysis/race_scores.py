"""推奨買目の表（1行 = 1点）から、1行 = 1レースの点数・投資・払戻・見込みを作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 地方の推奨買目.position_model import EV
from 地方の推奨買目.recommendation import STAKE

#: レースの見込みの列。見込みの回収率は、1点 100円で買ったときの 期待値の平均（= Σ 期待値 ÷ 点数）。期待の儲けは Σ（期待値 − 1）（100円単位）。
EXPECTED, EXPECTED_PROFIT = "expected", "expected_profit"


@dataclass(frozen=True)
class RaceScores:
    """``of(bets)`` は ``race_id``・``year``・``race_date``・``points``・``stake``・``returned``・``best``（いちばん大きい払戻）・
    ``EXPECTED``・``EXPECTED_PROFIT`` の表。"""

    def of(self, bets: pd.DataFrame) -> pd.DataFrame:
        b = bets.assign(_gain=bets[EV] - 1.0)
        grouped = b.groupby("race_id")
        races = grouped[["year", "race_date"]].first()
        races["points"] = grouped.size()
        races["stake"] = races["points"] * STAKE
        races["returned"] = grouped["payout"].sum().astype(float) * STAKE / 100.0
        races["best"] = grouped["payout"].max().astype(float) * STAKE / 100.0
        races[EXPECTED] = grouped[EV].mean()
        races[EXPECTED_PROFIT] = grouped["_gain"].sum()
        return races.reset_index()
