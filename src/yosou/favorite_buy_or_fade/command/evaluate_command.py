"""evaluate: 1年ごとに学習し直して、その年の1番人気の判定を確かめる。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments

from ..evaluation import EvaluationTables, StakePlan
from ..workflow import YEAR, TrainingDataReader, YearlyEvaluation
from .settings_argument import SettingsArgument
from .yosou_name import YOSOU_NAME


class EvaluateCommand:
    """``evaluate``: 方針の評価の年ごとに、その前年までで学習し直して判定し、年ごと・判定ごと・単位ごとの表を出す。

    ``--rows-out`` を渡すと、判定した1番人気1頭ずつの表も CSV で書く（JV-Data から作ったものなので ``reports/`` に置く）。
    """

    def __init__(self) -> None:
        self._settings_argument = SettingsArgument()

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "evaluate", help="1年ごとに学習し直して判定し、消し・単勝の当たり具合と回収率を出す", allow_abbrev=False,
        )
        self._settings_argument.add_to(parser)
        parser.add_argument("--rows-out", type=Path, default=None,
                            help="判定した1番人気1頭ずつの表を書く CSV のパス（reports/ の下に置く）")
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        settings = self._settings_argument.settings(args)
        with db.open_db(args.db) as con:
            data = TrainingDataReader(settings).read(con)
        rows = YearlyEvaluation(settings).run(data)
        if args.rows_out is not None:
            args.rows_out.parent.mkdir(parents=True, exist_ok=True)
            rows.to_csv(args.rows_out, index=False, encoding="utf-8-sig")
        return EvaluationTables(StakePlan.of(settings), YEAR).tables(rows)
