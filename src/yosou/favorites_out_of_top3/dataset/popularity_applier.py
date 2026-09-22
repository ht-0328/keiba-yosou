"""予測のときに使う人気を決める。"""

from __future__ import annotations

import pandas as pd

from ..repository import AnnouncedOddsRepository
from .popularity_input import PopularityInput


class PopularityApplier:
    """予測に使う「馬番 → 人気」を決める（設計書 06 の図2）。

    次の順で決める。

    1. 利用者が ``--pops`` で渡した人気。
    2. 元DB にそのレースの締め切り前の単勝オッズがあれば、オッズの小さい順に 1, 2, 3, … と人気を付ける。
    3. どちらも無ければ ``None``。元DB の出走の行に入っている人気（終わったレースなら確定単勝人気）が
       そのまま使われる。それも無ければ ``FavoriteSelector.prediction_runners()`` が止める。
    """

    def __init__(self, odds_repository: AnnouncedOddsRepository) -> None:
        self._odds_repository = odds_repository

    def resolve(self, race_id: str, given: PopularityInput | None) -> dict[int, int] | None:
        """予測に使う 馬番 → 人気。決められなければ ``None``。"""
        if given is not None:
            return given.as_mapping()
        odds = self._odds_repository.read(race_id)
        if odds.empty:
            return None
        return self._ranked(odds)

    def _ranked(self, odds: pd.DataFrame) -> dict[int, int] | None:
        """オッズの小さい順に人気を付ける。読めるオッズが無ければ ``None``。"""
        known = odds.dropna(subset=["horse_no", "odds"])
        if known.empty:
            return None
        ordered = known.sort_values(["odds", "horse_no"], kind="stable")
        return {int(horse_no): rank for rank, horse_no in enumerate(ordered["horse_no"], start=1)}
