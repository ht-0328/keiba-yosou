"""複勝の期待値で選ぶ。"""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from ...column_names import FORM_PROB, HORSE_NO, PLACE_ODDS, POPULARITY
from .form_rank_picker import FormRankPicker

_EXPECTED_VALUE = "_expected_value"


class ExpectedValuePicker:
    """「3着以内に入る確率 × 複勝の確定オッズ（下限）」が ``threshold`` 以上の馬を、期待値の高い順に全部選ぶ。

    確率は ``probability_column``（近走と適性の ``form_prob`` か、穴馬モデルの ``longshot_prob``）。
    ``top_only`` なら、本命（近走と適性の1位）だけを見る（1点の買い方用）。複勝オッズの無い馬は選ばない。
    """

    def __init__(self, threshold: float, probability_column: str = FORM_PROB, top_only: bool = False) -> None:
        self._threshold = threshold
        self._probability_column = probability_column
        self._top_only = top_only
        self._top_picker = FormRankPicker()

    def pick(self, runners: pd.DataFrame, count: int, taken: Collection[int]) -> list[int]:
        candidates = self._candidates(runners)
        valued = candidates.assign(**{_EXPECTED_VALUE: candidates[self._probability_column] * candidates[PLACE_ODDS]})
        rows = valued[valued[_EXPECTED_VALUE] >= self._threshold]
        ordered = rows.sort_values([_EXPECTED_VALUE, POPULARITY], ascending=[False, True])
        return [int(horse) for horse in ordered[HORSE_NO] if horse not in taken][:max(count, 0)]

    def _candidates(self, runners: pd.DataFrame) -> pd.DataFrame:
        if not self._top_only:
            return runners
        top = self._top_picker.pick(runners, 1, ())
        return runners[runners[HORSE_NO].isin(top)]
