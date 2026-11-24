"""組の表づくりの流れを進める。"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack
from datetime import date
from pathlib import Path

import pandas as pd

from 共通 import db

from yosou.shared.betting import TicketType
from yosou.shared.repository import RaceDayRange

from ..dataset import DEFAULT_BANDS, ComboTableBuilder, FinalMarket, FinalMarketLoader, HitLabeler, PayoutBand
from ..dataset.column_names import HIT, RACE_DATE, RACE_ID
from ..repository import ComboTableRepository, ComboTableWriter
from .table_year_result import TableYearResult

#: 元DB のロックを待つ上限（秒）。月ごとに短く開くので、ほかの道具が読み終えるのを待つ。
_LOCK_WAIT_SECONDS = 300.0


class TableWorkflow:
    """過去のレースの組の表を、年ごと・券種ごとのファイルに作る（学習と確かめのもと）。

    馬ごとの表を月ごとに区切り、その月の確定オッズの板と払戻を元DB から読んで、材料を付け（``ComboTableBuilder``）、
    当たったかを付けて（``HitLabeler``）、年のファイルに足していく。3連単は1年で数百万行になるので、1年ぶんをメモリに持たない。
    元DB は月ごとに読む間だけ開く（材料を作っている間は、ほかの道具を待たせない）。
    前に作った表のある券種・年は、``overwrite`` が偽なら飛ばす。
    """

    def __init__(self, db_path: Path | None, horses: pd.DataFrame, tables: ComboTableRepository,
                 ticket_types: Sequence[TicketType], *, overwrite: bool = False,
                 bands: Mapping[TicketType, PayoutBand] = DEFAULT_BANDS,
                 progress: Callable[[str], None] | None = None) -> None:
        """``db_path`` は元DB（None なら既定）、``horses`` は馬ごとの表、``ticket_types`` は表を作る券種、``progress`` は途中経過を受け取る関数。"""
        self._db_path = db_path
        self._horses = horses
        self._tables = tables
        self._ticket_types = tuple(ticket_types)
        self._overwrite = overwrite
        self._builder = ComboTableBuilder(bands)
        self._labeler = HitLabeler()
        self._progress = progress or (lambda message: None)

    def run(self, first_day: date, last_day: date) -> list[TableYearResult]:
        """開催日が ``first_day`` 以上 ``last_day`` 以下のレースの表を作る。年の途中で区切ると、その年のファイルは区切った範囲だけになる。"""
        days = self._horses[RACE_DATE]
        horses = self._horses[(days >= pd.Timestamp(first_day)) & (days <= pd.Timestamp(last_day))]
        results: list[TableYearResult] = []
        for year, year_horses in horses.groupby(horses[RACE_DATE].dt.year, sort=True):
            results += self._build_year(int(year), year_horses)
        return results

    def _build_year(self, year: int, horses: pd.DataFrame) -> list[TableYearResult]:
        """1年ぶん。まだ無い（か作り直す）券種の表を、月ごとに足して書く。"""
        wanted = [ticket_type for ticket_type in self._ticket_types if self._overwrite or not self._tables.exists(ticket_type, year)]
        skipped = [TableYearResult(ticket_type, year, 0, 0, True) for ticket_type in self._ticket_types if ticket_type not in wanted]
        if not wanted:
            return skipped
        hit_counts = dict.fromkeys(wanted, 0)
        with ExitStack() as stack:
            writers = {ticket_type: stack.enter_context(self._tables.writer(ticket_type, year)) for ticket_type in wanted}
            for month, month_horses in horses.groupby(horses[RACE_DATE].dt.month, sort=True):
                self._build_month(month_horses, writers, hit_counts)
                self._progress(f"組の表: {year}年{int(month)}月")
        built = [TableYearResult(ticket_type, year, writers[ticket_type].row_count, hit_counts[ticket_type], False) for ticket_type in wanted]
        return skipped + built

    def _build_month(self, horses: pd.DataFrame, writers: Mapping[TicketType, ComboTableWriter],
                     hit_counts: dict[TicketType, int]) -> None:
        """1か月ぶん。板と払戻を読み、券種ごとの表を作って、年のファイルに足す。"""
        wanted = list(writers)
        market = self._market(horses, wanted)
        race_dates = horses.groupby(RACE_ID)[RACE_DATE].first()
        tables = self._builder.build(horses, market.boards, wanted)
        for ticket_type, table in tables.items():
            labeled = self._labeler.label(ticket_type, table, market.payouts[ticket_type], race_dates)
            writers[ticket_type].write(labeled)
            hit_counts[ticket_type] += int(labeled[HIT].sum())

    def _market(self, horses: pd.DataFrame, payout_types: Sequence[TicketType]) -> FinalMarket:
        """その月の確定オッズの板と払戻。元DB は読む間だけ開く。"""
        days = RaceDayRange(horses[RACE_DATE].min().date(), horses[RACE_DATE].max().date())
        with db.open_db(self._db_path, lock_timeout=_LOCK_WAIT_SECONDS) as con:
            return FinalMarketLoader(con).load(days, set(horses[RACE_ID]), payout_types)
