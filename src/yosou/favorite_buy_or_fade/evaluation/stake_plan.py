"""判定ごとの掛け金。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.dataset.column_names import PLACE_PAYOUT, WIN_PAYOUT

from ..decision import PLACE_ONLY, WIN_AND_PLACE
from ..setting import BuyOrFadeSettings

#: 払戻は 100円あたりの金額。
_PAYOUT_UNIT = 100


@dataclass(frozen=True)
class StakePlan:
    """判定ごとの単勝・複勝の掛け金（円。設計書 16）。「消す」は買わない。"""

    win_and_place_win: int
    win_and_place_place: int
    place_only_place: int

    @classmethod
    def of(cls, settings: BuyOrFadeSettings) -> StakePlan:
        return cls(settings.win_and_place_win_stake, settings.win_and_place_place_stake,
                   settings.place_only_place_stake)

    def invested(self, decisions: pd.Series) -> pd.Series:
        """行ごとの投資（円）。"""
        return self._win_stakes(decisions) + self._place_stakes(decisions)

    def returned(self, decisions: pd.Series, payouts: pd.DataFrame) -> pd.Series:
        """行ごとの払戻（円）。``payouts`` は単勝と複勝の払戻（100円あたり。当たらなければ 0）の列を持つ表。"""
        win = self._win_stakes(decisions) / _PAYOUT_UNIT * payouts[WIN_PAYOUT]
        place = self._place_stakes(decisions) / _PAYOUT_UNIT * payouts[PLACE_PAYOUT]
        return win + place

    def _win_stakes(self, decisions: pd.Series) -> pd.Series:
        return (decisions == WIN_AND_PLACE).astype(float) * self.win_and_place_win

    def _place_stakes(self, decisions: pd.Series) -> pd.Series:
        by_kind = {WIN_AND_PLACE: self.win_and_place_place, PLACE_ONLY: self.place_only_place}
        return decisions.map(by_kind).fillna(0).astype(float)
