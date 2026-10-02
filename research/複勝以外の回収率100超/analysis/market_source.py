"""市場の組の確率（どの券種のオッズから作るかを選べる）に、馬ごとの上げ下げを掛ける確率の出どころ。"""

from __future__ import annotations

import numpy as np

from 回収率100超.analysis.tickets import TicketKind

from .horse_uplift import HorseUplift
from .market_combo_table import MarketComboTable
from .pool_derivation import PoolDerivation

#: 組の確率を作る元の券種。
OWN, TRIFECTA, TRIO = "own", "trifecta", "trio"
#: 表に出す名前。
ORIGIN_NAMES: dict[str, str] = {OWN: "その券種自身", TRIFECTA: "3連単から", TRIO: "3連複から"}


class MarketSource:
    """研究「回収率100超」の ``YearTicketScorer`` に渡す確率の出どころ（``ComboSource``）。

    - ``origin`` が ``own``: 買う券種自身のオッズから作った組の確率（研究の計画の案②の出発点）。
    - ``origin`` が ``trifecta``・``trio``: 3連単・3連複のオッズから作った組の確率（案①）。
    その確率に、``HorseUplift`` で馬ごとの上げ下げを掛ける（強さ 0 なら掛けない。案②・③）。
    """

    def __init__(self, origin: str, tables: dict[str, MarketComboTable], uplift: HorseUplift) -> None:
        self._origin = origin
        self._tables = tables
        self._uplift = uplift
        self._derivation = PoolDerivation()

    def table(self, kind: TicketKind, rid: int) -> np.ndarray | None:
        base = self._base(kind, rid)
        return None if base is None else self._uplift.apply(kind, rid, base)

    def _base(self, kind: TicketKind, rid: int) -> np.ndarray | None:
        origin = self._tables[self._origin].get(rid)
        if origin is None:
            return None
        if self._origin == TRIFECTA:
            return self._derivation.from_trifecta(kind, origin)
        if self._origin == TRIO:
            return self._derivation.from_trio(kind, origin)
        return origin
