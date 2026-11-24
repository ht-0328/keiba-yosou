"""tables: 過去のレースの組の表を作る。"""

from __future__ import annotations

import argparse
from datetime import date

from 共通.render import Table

from yosou.shared.command import CommonArguments

from ..dataset.column_names import RACE_DATE
from ..repository import ComboTableRepository, HorseTableRepository
from ..workflow import TableWorkflow, TableYearResult
from .folder_arguments import add_folder_argument
from .progress import print_progress
from .ticket_argument import add_ticket_argument, ticket_types_of
from .yosou_name import YOSOU_NAME

#: 表を作る最初の開催日の既定。
DEFAULT_FIRST_DAY = date(2015, 1, 1)
_BUILT, _SKIPPED = "作った", "済んでいるので飛ばした"


class TablesCommand:
    """``tables``: 馬ごとの表と元DB の確定オッズの板・払戻から、券種ごと・年ごとの組の表（材料・出発点・当たったか）を作る。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("tables", help="過去のレースの組の表（学習と確かめのもと）を作る", allow_abbrev=False)
        parser.add_argument(
            "--from", dest="first_day", type=date.fromisoformat, default=DEFAULT_FIRST_DAY,
            help=f"表を作る最初の開催日（既定: {DEFAULT_FIRST_DAY}）",
        )
        parser.add_argument(
            "--to", dest="last_day", type=date.fromisoformat, default=None,
            help="表を作る最後の開催日（省略すると、馬ごとの表の最後の開催日）",
        )
        parser.add_argument("--force", action="store_true", help="前に作った表のある券種・年も作り直す（省略すると飛ばす）")
        add_ticket_argument(parser)
        add_folder_argument(parser, "horses")
        add_folder_argument(parser, "tables")
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        horses = HorseTableRepository(args.horses).load()
        last_day = args.last_day or horses[RACE_DATE].max().date()
        workflow = TableWorkflow(
            args.db, horses, ComboTableRepository(args.tables), ticket_types_of(args), overwrite=args.force, progress=print_progress,
        )
        results = workflow.run(args.first_day, last_day)
        return [self._table(results, args.first_day, last_day)]

    def _table(self, results: list[TableYearResult], first_day: date, last_day: date) -> Table:
        rows = [
            [result.ticket_type.label, result.year, result.row_count, result.hit_count, _SKIPPED if result.was_skipped else _BUILT]
            for result in results
        ]
        return Table(["券種", "年", "対象の組", "当たった組", "状態"], rows, title=f"組の表（開催日 {first_day}〜{last_day}）")
