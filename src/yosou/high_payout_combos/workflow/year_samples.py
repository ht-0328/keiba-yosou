"""年ごとの学習の行を、保存した組の表から作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType

from ..dataset import MissSampling
from ..repository import ComboTableRepository


class YearSamples:
    """保存した組の表（``ComboTableRepository``）を年ごとに読み、学習の行（当たりは全部・外れは間引いて重みつき。``MissSampling``）にする。

    1年ぶんの表を読んでは間引くので、メモリに残るのは間引いた行だけ（3連単でも1年で数万行）。
    """

    def __init__(self, tables: ComboTableRepository, sampling: MissSampling | None = None) -> None:
        self._tables = tables
        self._sampling = sampling or MissSampling()

    def of(self, ticket_type: TicketType, year: int) -> pd.DataFrame:
        """その券種・年の学習の行。"""
        return self._sampling.sample(ticket_type, self._tables.load(ticket_type, year), year)

    def by_year(self, ticket_type: TicketType) -> dict[int, pd.DataFrame]:
        """その券種の、表のある年ぜんぶの学習の行（年 → 行。古い順）。"""
        return {year: self.of(ticket_type, year) for year in self._tables.years(ticket_type)}
