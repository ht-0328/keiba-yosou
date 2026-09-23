"""予測のときに使う単勝オッズを決める。"""

from __future__ import annotations

from ..repository import AnnouncedOddsRepository
from .odds_input import OddsInput


class OddsResolver:
    """予測に使う「馬番 → 単勝オッズ」を決める（手本の設計書 06 の図2）。オッズを使う予想が使う。

    次の順で決める。

    1. 利用者が ``--odds`` で渡したオッズ。
    2. 元DB にそのレースの締め切り前の単勝オッズ（時系列オッズ）があれば、そのいちばん新しい断面。
    3. どちらも無ければ ``None``。元DB の出走の行に入っている単勝オッズ（終わったレースなら確定オッズ）が
       そのまま使われる。それも無ければ ``RequiredInfoCheck`` が、渡し方を案内して止める。
    """

    def __init__(self, odds_repository: AnnouncedOddsRepository) -> None:
        self._odds_repository = odds_repository

    def resolve(self, race_id: str, given: OddsInput | None) -> dict[int, float] | None:
        """予測に使う 馬番 → 単勝オッズ。決められなければ ``None``。"""
        if given is not None:
            return given.as_mapping()
        announced = self._odds_repository.read(race_id).dropna(subset=["horse_no", "odds"])
        if announced.empty:
            return None
        return {int(horse_no): float(odds)
                for horse_no, odds in zip(announced["horse_no"], announced["odds"], strict=True)}
