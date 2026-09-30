"""train: 学習する。"""

from __future__ import annotations

import argparse
from itertools import chain
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments, PlacePriceStep, TrainingReportTables
from yosou.shared.workflow import SegmentedTraining

from ..dataset import dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import SEGMENTS, TIMINGS
from .buy_line_step import BuyLineStep
from .period_arguments import PeriodArguments
from .yosou_name import YOSOU_NAME


class TrainCommand:
    """``train``: 区分（中穴・大穴）ごと・3つの時点ごとに2つのモデルを学習して保存し、検証データでの当たり具合を出す。

    学習のあとに、複勝の見込みの倍率（学習データの期間の払戻から決めたもの）も保存する（予測で複勝の期待値を出すため）。
    最後に、時点ごと・区分ごとの「買い」の線（検証データで決めたもの）も保存する（設計書 16 の 3）。
    """

    def __init__(self) -> None:
        self._period_arguments = PeriodArguments()

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "train", help="3つの時点（木曜・前日・当日）ごとに2つのモデルを学習して保存する", allow_abbrev=False,
        )
        parser.add_argument(
            "--config", type=Path, default=None,
            help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）",
        )
        self._period_arguments.add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データを読む段だけ。学習は DB を閉じてから行い、ほかの道具を待たせない。"""
        period = self._period_arguments.period(args)
        with db.open_db(args.db) as con:
            training = SegmentedTraining(SEGMENTS, dataset_builder(con), period, args.models, TIMINGS, DEFAULT_SETTINGS_PATH)
            training_data = training.read_training_data()
        reports = training.train(training_data, args.config)
        tables = list(chain.from_iterable(TrainingReportTables(report, label).tables() for label, report in reports))
        place_price = PlacePriceStep().run(training_data.between(None, period.valid_first_day), args.models)
        buy_lines = BuyLineStep(SEGMENTS, TIMINGS).run(training_data, period, args.models)
        return [*tables, place_price, *buy_lines]
