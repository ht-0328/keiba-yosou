"""目的変数（券種ごとの荒れ具合）を付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import as_numbers
from yosou.shared.repository.race_payout_repository import VOID, YEN

from .bet_type import BetType
from .upset_level_rule import UpsetLevelRule


class UpsetLevelLabeler:
    """レースごとの払戻から、券種ごとの荒れ具合（0〜3）の4列を付ける（設計書 10 の「作り方」）。``RaceTargetLabeler`` を守る。

    - 払戻は共通の ``RacePayoutRepository`` が読んだもの（同着は最大の額）。
    - 発売が無い（払戻が無い）・不成立・特払の券種は欠損値にし、その券種のモデルの学習から外す。返還は普通に扱う。
    """

    def __init__(self, rule: UpsetLevelRule) -> None:
        self._rule = rule

    @property
    def label_names(self) -> tuple[str, ...]:
        """目的変数の列の名前（券種の順）。"""
        return tuple(bet.column_name for bet in BetType)

    def build(self, races: pd.DataFrame) -> pd.DataFrame:
        """行の並びと index は ``races`` と同じ。"""
        return pd.DataFrame({bet.column_name: self._levels(races, bet) for bet in BetType}, index=races.index)

    def _levels(self, races: pd.DataFrame, bet: BetType) -> pd.Series:
        yen = as_numbers(races[f"{bet.key}_{YEN}"])
        is_void = races[f"{bet.key}_{VOID}"].fillna(False).astype(bool)
        return self._rule.levels_of(bet, yen).where(~is_void)
