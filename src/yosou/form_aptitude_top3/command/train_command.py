"""train: 学習する。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import duckdb

from 共通.render import Table

from ..dataset import TEST_FIRST_DAY, VALID_FIRST_DAY, DatasetBuilder, PeriodSplitter
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
        parser.add_argument(
            "--valid-from", type=date.fromisoformat, default=VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {VALID_FIRST_DAY}。これより前が学習データ）",
        )
        parser.add_argument(
            "--test-from", type=date.fromisoformat, default=TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {TEST_FIRST_DAY}）",
        )
        CommonArguments().add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> list[Table]:
        workflow = TrainingWorkflow(
            DatasetBuilder.for_database(con),
            PeriodSplitter(args.valid_from, args.test_from),
            ModelRepository(args.models, MEMBER_TYPES),
        )
        report = workflow.run(args.config)
        return TrainingReportTables(report).tables()
