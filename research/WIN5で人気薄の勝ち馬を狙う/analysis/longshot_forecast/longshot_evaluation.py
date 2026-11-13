"""作り方ごとの人気薄の1着の予想を、人気薄の中の並べ方と確率の当たり具合で比べ、探索期間で1つ選ぶ。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from 共通.render import Table

from .evaluation_frame import CURRENT, MARKET
from .ordering_capture_table import OrderingCaptureTable
from .probability_fit_table import ProbabilityFitTable

#: 期間（探索・確認）の境目。
CONFIRM_START = pd.Timestamp("2025-01-01")
EXPLORE, CONFIRM = "2019〜2024年", "2025年〜"
#: 選ぶときに見る上位の頭数。
CHOOSE_TOP = 3


@dataclass(frozen=True)
class LongshotEvaluation:
    """``frame`` は ``EvaluationFrame`` の表、``labels`` は作り方の名前、``win5_races`` は WIN5 の対象レースのレースID。"""

    frame: pd.DataFrame
    labels: Sequence[str]
    win5_races: frozenset[str]

    def tables(self) -> list[Table]:
        columns = [MARKET, CURRENT, *self.labels]
        scopes = list(product(("平地の全レース", "WIN5 の対象レース"), (EXPLORE, CONFIRM)))
        capture = [OrderingCaptureTable().build(self._part(scope, period), columns, f"人気薄の中の並べ方（{scope}・{period}）")
                   for scope, period in scopes]
        fit = [ProbabilityFitTable().build(self._part(scope, period), columns, f"人気薄の1着の確率の当たり具合（{scope}・{period}）")
               for scope, period in scopes]
        return [*capture, *fit]

    def chosen(self) -> str:
        """探索期間・平地の全レースで、上位3頭に勝ち馬を置けた割合がいちばん大きい作り方（同じなら対数損失の小さいほう）。"""
        part = self._part("平地の全レース", EXPLORE)
        won_races = part.loc[part["won"] == 1, "race_id"].unique()
        chosen = part.loc[part["race_id"].isin(won_races)]
        scores = {label: self._capture(chosen, label) for label in self.labels}
        return max(self.labels, key=lambda label: (scores[label], -self._log_loss(part, label)))

    def _part(self, scope: str, period: str) -> pd.DataFrame:
        frame = self.frame
        in_period = frame["race_date"] < CONFIRM_START if period == EXPLORE else frame["race_date"] >= CONFIRM_START
        part = frame.loc[in_period]
        return part if scope == "平地の全レース" else part.loc[part["race_id"].isin(self.win5_races)]

    @staticmethod
    def _capture(chosen: pd.DataFrame, label: str) -> float:
        rank = chosen[label].groupby(chosen["race_id"]).rank(ascending=False, method="first")
        return float((rank[chosen["won"] == 1] <= CHOOSE_TOP).mean())

    @staticmethod
    def _log_loss(part: pd.DataFrame, label: str) -> float:
        clipped = part[label].clip(1e-6, 1 - 1e-6).to_numpy()
        won = part["won"].to_numpy()
        return float(-np.mean(won * np.log(clipped) + (1 - won) * np.log(1 - clipped)))
