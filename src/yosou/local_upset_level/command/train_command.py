"""train: 学習する。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import ClassTrainingReportTables, CommonArguments
from yosou.shared.evaluation import ClassModelEvaluator
from yosou.shared.ml_model import CLASS_MEMBER_TYPES
from yosou.shared.workflow import TrainingWorkflow
from yosou.upset_level.dataset import BET_CHOICES, BetType, UpsetLevel
from yosou.upset_level.workflow import model_repositories

from ..dataset import TrainingDataCache
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import DEFAULT_CACHE_DIR, TIMING_LABELS, TIMINGS
from ..yosou_name import YOSOU_NAME
from .period_arguments import PeriodArguments
from .upset_threshold_table import UpsetThresholdTable


class TrainCommand:
    """``train``: 学習データ（1行 = 1レース。当日の馬場傾向のレースの値つき）を1回作り、券種ごと・3つの時点ごとに2つのモデルを学習して保存し、
    検証データでの当たり具合と、「中荒れ以上の確率」のしきい値ごとの数え上げを出す。

    学習データは作るのに 30〜60分かかるので、``--cache`` の場所に pickle でとっておき、2回目からは読むだけ（``--rebuild`` で作り直す）。
    元DB を開くのは学習データを作る段だけ。学習は DB を閉じてから行い、ほかの道具を待たせない。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "train", help="券種ごと・3つの時点（出馬表・前日・当日）ごとに2つのモデルを学習して保存する", allow_abbrev=False,
        )
        parser.add_argument("--config", type=Path, default=None, help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）")
        parser.add_argument(
            "--bet", nargs="*", default=None, choices=[bet.label for bet in BetType], metavar="券種",
            help=f"学習する券種: {BET_CHOICES}（省略すると4つ全部）",
        )
        parser.add_argument(
            "--cache", type=Path, default=DEFAULT_CACHE_DIR,
            help=f"学習データの pickle をとっておく場所（既定: {DEFAULT_CACHE_DIR}）。あれば読むだけ",
        )
        parser.add_argument("--rebuild", action="store_true", help="とっておいた学習データがあっても作り直す（新しい成績がたまったとき）")
        PeriodArguments().add_to(parser)
        CommonArguments(YOSOU_NAME, db.LOCAL).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        period = PeriodArguments().period_of(args)
        data = TrainingDataCache(args.cache).load_or_build(lambda: db.open_db(args.db, default=db.LOCAL), period, rebuild=args.rebuild)
        repositories = model_repositories(args.models)
        tables: list[Table] = []
        for bet in self._bets(args):
            workflow = TrainingWorkflow(
                None, period, repositories[bet], TIMINGS, DEFAULT_SETTINGS_PATH,
                member_types=CLASS_MEMBER_TYPES, evaluator=ClassModelEvaluator(),
            )
            report = workflow.train(data.with_label(bet.column_name), args.config)
            tables += ClassTrainingReportTables(report, UpsetLevel.labels(), bet.label, timing_labels=TIMING_LABELS).tables()
            tables.append(UpsetThresholdTable(bet, report, repositories[bet]).table())
        return tables

    def _bets(self, args: argparse.Namespace) -> list[BetType]:
        """``--bet`` で渡された券種。渡されなければ4つ全部。"""
        if not args.bet:
            return list(BetType)
        return [BetType.parse(text) for text in args.bet]
