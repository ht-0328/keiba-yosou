"""馬ごとの表と5券種の板から、券種ごとの組の表を作る。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from yosou.shared.betting import TicketType

from ..feature import REQUIRED_MARKETS, TICKET_TYPES
from .default_bands import DEFAULT_BANDS
from .horse_materials import HorseMaterials
from .market_table_builder import MarketTableBuilder
from .payout_band import PayoutBand
from .race_materials import RaceMaterials
from .ticket_table_assembler import TicketTableAssembler
from .trifecta_pool_win import TrifectaPoolWin


class ComboTableBuilder:
    """馬ごとの表（1頭1行。何レースぶんでもよい）と、5券種のオッズの板（列 ``race_id``・``combo``・``odds``）から、
    券種ごとの組の表（1行 = 1つの組。ID・オッズ・出発点・材料）を作る。

    過去レースの学習用の表づくり（板は確定オッズ）でも、本番の1レースの予測（板は締め切り前の断面）でも、このクラスを使う。
    板の出どころは問わない。払戻（当たったか）は付けない（``HitLabeler``）。

    板が足りない券種は、戻り値の辞書に入れない（誤りにしない）。足りないとは、その券種の板が無い、3連単の板が無い
    （市場の確率 t と ``psup`` が作れない）、ほかの券種の市場の材料に要る板が無い（``REQUIRED_MARKETS``）のどれか。
    """

    def __init__(self, bands: Mapping[TicketType, PayoutBand] = DEFAULT_BANDS) -> None:
        self._bands = bands
        self._markets = MarketTableBuilder()

    def build(self, horses: pd.DataFrame, boards: Mapping[TicketType, pd.DataFrame],
              ticket_types: Sequence[TicketType] = TICKET_TYPES) -> dict[TicketType, pd.DataFrame]:
        """``ticket_types`` は表を作る券種（省略すると5つ全部）。板は、作らない券種のぶんも要る（ほかの券種の市場の材料に使う）。"""
        markets = self._markets.build(horses, boards)
        buildable = [ticket_type for ticket_type in ticket_types if self._is_buildable(ticket_type, markets)]
        if not buildable:
            return {}
        materials = HorseMaterials().of(horses, TrifectaPoolWin().of(boards[TicketType.TRIFECTA]))
        assembler = TicketTableAssembler(markets, materials, RaceMaterials().of(materials))
        return {ticket_type: assembler.table(self._bands[ticket_type]) for ticket_type in buildable}

    def _is_buildable(self, ticket_type: TicketType, markets: Mapping[TicketType, pd.DataFrame]) -> bool:
        """その券種の帯があり、その券種の板と、材料に要るほかの券種の板がそろっているか。"""
        needed = (ticket_type, *REQUIRED_MARKETS[ticket_type])
        return ticket_type in self._bands and all(each in markets for each in needed)
