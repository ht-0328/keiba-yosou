"""5券種の板から、券種ごとの市場の表を作る。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import HARVILLE, MARKET, ComboBlendFeatures, HorseStrength, PoolFolding, TrifectaSources, split_combo

from ..feature import TICKET_TYPES
from ..feature.column_names import COMBO, ODDS, RACE_ID


class MarketTableBuilder:
    """馬ごとの表と、券種ごとのオッズの板（列 ``race_id``・``combo``・``odds``）から、券種ごとの市場の表（1行 = 1組）を作る。

    市場の確率は共有の部品（``yosou.shared.combo_value``）で作る。``log_own`` はその券種のオッズの逆数をレースで合計 1
    （ワイドは 3）にそろえた値 q の対数、``log_trifecta`` は3連単の市場の確率をその券種の組に足し合わせた値 t の対数。
    列は ``race_id``・``combo``・``h1``…・``odds``・``log_own``・``log_trifecta`` ほか。馬ごとの表に無いレースの組は入れない。
    オッズの無い組、3連単から作れない組、馬ごとの表に無い馬や市場の見立ての無い馬を含む組は落ちる。

    板の無い（か空の）券種は、戻り値の辞書に入れない。3連単の板が無ければ、どの券種も作れないので空の辞書を返す。
    板の出どころ（確定オッズか、締め切り前の断面か）は問わない。
    """

    def __init__(self) -> None:
        self._features = ComboBlendFeatures()
        self._folding = PoolFolding()

    def build(self, horses: pd.DataFrame, boards: Mapping[TicketType, pd.DataFrame]) -> dict[TicketType, pd.DataFrame]:
        races = set(horses[RACE_ID].astype(str))
        cleaned = {ticket_type: self._cleaned(boards[ticket_type], races) for ticket_type in TICKET_TYPES if ticket_type in boards}
        present = {ticket_type: board for ticket_type, board in cleaned.items() if not board.empty}
        if TicketType.TRIFECTA not in present:
            return {}
        strength = HorseStrength().of(horses)
        sources = TrifectaSources().of(split_combo(present[TicketType.TRIFECTA], 3), strength)
        return {ticket_type: self._market(ticket_type, board, sources, strength) for ticket_type, board in present.items()}

    def _market(self, ticket_type: TicketType, board: pd.DataFrame, sources: pd.DataFrame, strength: pd.DataFrame) -> pd.DataFrame:
        folded = self._folding.fold(ticket_type, sources, [MARKET, HARVILLE])
        return self._features.build(ticket_type, board, folded, strength)

    def _cleaned(self, board: pd.DataFrame, races: set[str]) -> pd.DataFrame:
        """板の型をそろえ、馬ごとの表にあるレースの、オッズのある組だけにする。"""
        typed = pd.DataFrame({
            RACE_ID: board[RACE_ID].astype(str), COMBO: board[COMBO].astype(str), ODDS: pd.to_numeric(board[ODDS], errors="coerce"),
        })
        return typed[typed[RACE_ID].isin(races) & (typed[ODDS] > 0)].reset_index(drop=True)
