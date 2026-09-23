"""train: 学習する。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments, PlacePriceStep, TrainingReportTables
from yosou.shared.dataset import (
    DEFAULT_TEST_FIRST_DAY,
    DEFAULT_TRAIN_FIRST_DAY,
    DEFAULT_VALID_FIRST_DAY,
    TrainingPeriod,
)
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import TIMINGS
from .yosou_name import YOSOU_NAME


class TrainCommand:
    """``train``: 3つの時点ごとに2つのモデルを学習して保存し、検証データでの当たり具合を出す。

    学習のあとに、複勝の見込みの倍率（学習データの期間の払戻から決めたもの）も保存する（予測で複勝の期待値を出すため）。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "train", help="3つの時点ごとに2つのモデルを学習して保存する", allow_abbrev=False,
        )
        parser.add_argument(
            "--config", type=Path, default=None,
            help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）",
        )
        self._add_period_arguments(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データを読む段だけ。学習は DB を閉じてから行い、ほかの道具を待たせない。"""
        period = TrainingPeriod.starting(
            args.train_from, args.valid_from, args.test_from, warmup_first_day=args.warmup_from,
        )
        with db.open_db(args.db) as con:
            workflow = TrainingWorkflow(
                dataset_builder(con), period, ModelRepository(args.models, MEMBER_TYPES),
                TIMINGS, DEFAULT_SETTINGS_PATH,
            )
            training_data = workflow.read_training_data()
        report = workflow.train(training_data, args.config)
        place_price = PlacePriceStep().run(report.split.train, args.models)
        return [*TrainingReportTables(report).tables(), place_price]

    def _add_period_arguments(self, parser: argparse.ArgumentParser) -> None:
        """学習データの期間の区切り（設計書 08 の 3）。古い順に ウォームアップ → 学習 → 検証 → テスト。"""
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=None,
            help="ウォームアップ期間の最初の開催日。この日からの出走を過去走の計算にだけ使い、サンプルにしない"
                 "（省略すると、学習データの最初の日の前の年の1月1日）",
        )
        group.add_argument(
            "--train-from", type=date.fromisoformat, default=DEFAULT_TRAIN_FIRST_DAY,
            help=f"学習データの最初の開催日（既定: {DEFAULT_TRAIN_FIRST_DAY}）",
        )
        group.add_argument(
            "--valid-from", type=date.fromisoformat, default=DEFAULT_VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {DEFAULT_VALID_FIRST_DAY}。これより前が学習データ）",
        )
        group.add_argument(
            "--test-from", type=date.fromisoformat, default=DEFAULT_TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {DEFAULT_TEST_FIRST_DAY}）",
        )
