"""1つの組（前半・後半・着順）の予測の入れ物。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID

#: 1頭ごとの予測の列（前半の組）。先頭の確率と、先団・中団・後方の確率。
LEADER_PROBABILITY = "p_leader"
FRONT_PROBABILITY, MIDDLE_PROBABILITY, BACK_PROBABILITY = "p_front", "p_middle", "p_back"
#: 1レースごとの予測の列（前半の組）。スロー・平均・ハイの確率と、前半タイムの基準との差の 10%・50%・90% の値。
SLOW_PROBABILITY, EVEN_PROBABILITY, HIGH_PROBABILITY = "p_slow", "p_even", "p_high"
FIRST_HALF_QUANTILES: tuple[str, str, str] = ("first_q10", "first_q50", "first_q90")
#: 1頭ごとの予測の列（後半の組）。4コーナーの位置と上がりの速さ。
CORNER4_PREDICTION, CLOSING_PREDICTION = "corner4_pred", "closing_pred"
#: 1レースごとの予測の列（後半の組）。後半タイムの基準との差の 10%・50%・90% の値。
SECOND_HALF_QUANTILES: tuple[str, str, str] = ("second_q10", "second_q50", "second_q90")
#: 1頭ごとの予測の列（着順の組）。1着の確率（⑦）と、比べる基準（前半・後半を入れないモデル）の1着の確率。
WIN_PROBABILITY, PLAIN_WIN_PROBABILITY = "p_win", "p_win_plain"
#: 1頭ごとの表と1レースごとの表の鍵。
HORSE_KEY: tuple[str, str] = (RACE_ID, HORSE_ID)
RACE_KEY: tuple[str] = (RACE_ID,)


@dataclass(frozen=True)
class GroupForecast:
    """1つの組の予測（設計書 04 の「feature/」）。後の組の特徴量（S・T）の元になる。

    - ``horses``: 1行 = 1頭（列 ``レースID``・``馬ID`` と、1頭ごとの予測の列）。
    - ``races``: 1行 = 1レース（列 ``レースID`` と、1レースごとの予測の列）。1レースごとの予想が無い組は空の表。
    """

    horses: pd.DataFrame
    races: pd.DataFrame

    @classmethod
    def concat(cls, parts: Sequence[GroupForecast]) -> GroupForecast:
        """年ごとの予測をつなぐ。"""
        return cls(
            pd.concat([part.horses for part in parts], ignore_index=True),
            pd.concat([part.races for part in parts], ignore_index=True),
        )

    def horse_rows(self, ids: pd.DataFrame) -> pd.DataFrame:
        """``ids``（列 ``レースID``・``馬ID``）の行の並びに合わせた1頭ごとの予測。無い行は欠損値。index は ``ids`` と同じ。"""
        return self._aligned(self.horses, ids, list(HORSE_KEY))

    def race_rows(self, ids: pd.DataFrame) -> pd.DataFrame:
        """``ids``（列 ``レースID``）の行の並びに合わせた1レースごとの予測。1頭ごとの行に配ることもできる。"""
        return self._aligned(self.races, ids, list(RACE_KEY))

    def _aligned(self, table: pd.DataFrame, ids: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        keyed = ids[keys].astype("str")
        found = keyed.merge(table.astype({key: "str" for key in keys}), on=keys, how="left")
        return found.drop(columns=keys).set_axis(ids.index)
