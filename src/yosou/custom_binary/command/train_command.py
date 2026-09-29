"""train: 指定した条件で学習する。"""

import argparse
from pathlib import Path

from 共通.render import Table

from ..feature.registrations import default_registry
from ..workflow import TrainingWorkflow
from .common_options import CommonOptions
from .training_tables import TrainingTables


class TrainCommand:
    """``train``: 設定の YAML で学習して ``reports/特徴量と条件を選んで予想/<name>/`` に保存し、検証期間の成績を出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("train", help="指定した条件で学習", allow_abbrev=False)
        parser.add_argument("--config", type=Path, required=True, help="設定YAMLファイル")
        options = CommonOptions()
        options.add_output(parser)
        options.add_db(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        trained = TrainingWorkflow(default_registry(), args.db).run(args.config)
        return TrainingTables(trained).tables()
