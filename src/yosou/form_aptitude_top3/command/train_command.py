"""train: 学習する。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import duckdb

from 共通.render import Table

from ..dataset import (
    DEFAULT_TEST_FIRST_DAY,
    DEFAULT_TRAIN_FIRST_DAY,
    DEFAULT_VALID_FIRST_DAY,
    DEFAULT_WARMUP_YEARS,
    DatasetBuilder,
    TrainingPeriod,
)
from ..ml_model import MEMBER_TYPES
from ..repository import ModelRepository
from ..workflow import TrainingWorkflow
from .common_arguments import CommonArguments
from .training_report_tables import TrainingReportTables


class TrainCommand:
    """``train``: 3つの時点ごとに2つのモデルを学習して保存し、検証データでの当たり具合を出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "train", help="3つの時点ごとに2つのモデルを学習して保存する", allow_abbrev=False,
        )
        parser.add_argument(
            "--config", type=Path, default=None,
            help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）",
        )
        self._add_period_arguments(parser)
        CommonArguments().add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> list[Table]:
        period = TrainingPeriod.starting(
            args.train_from, args.valid_from, args.test_from, warmup_first_day=args.warmup_from,
        )
        workflow = TrainingWorkflow(
            DatasetBuilder.for_database(con), period, ModelRepository(args.models, MEMBER_TYPES),
        )
        report = workflow.run(args.config)
        return TrainingReportTables(report).tables()

    def _add_period_arguments(self, parser: argparse.ArgumentParser) -> None:
        """学習データの期間の区切り（設計書 08 の 3）。古い順に ウォームアップ → 学習 → 検証 → テスト。"""
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=None,
            help="ウォームアップ期間の最初の開催日。この日からの出走を過去走の計算にだけ使い、サンプルにしない"
                 f"（省略すると、学習データの最初の日の {DEFAULT_WARMUP_YEARS} 年前）",
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
