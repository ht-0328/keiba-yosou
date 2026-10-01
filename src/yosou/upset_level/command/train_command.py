"""train: 学習する。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import ClassTrainingReportTables, CommonArguments
from yosou.shared.dataset import DEFAULT_TEST_FIRST_DAY, DEFAULT_VALID_FIRST_DAY, TrainingPeriod
from yosou.shared.evaluation import ClassModelEvaluator, TrainingReport
from yosou.shared.ml_model import CLASS_MEMBER_TYPES, EnsembleModel
from yosou.shared.repository import ModelRepository
from yosou.shared.setting import HyperparameterSettings
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import BET_CHOICES, BetType, UpsetLevel, race_dataset_builder
from ..evaluation import ClassShareBaseline, FavoriteOddsBaseline, UpsetThresholdSummary, UserRuleBaseline
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import TIMINGS, model_repositories
from .upset_comparison_tables import UpsetComparisonTables
from .yosou_name import YOSOU_NAME

#: 学習データの始まりの既定（設計書 08 の 4・15 の 5）。DB にある全部（2011年をウォームアップにして 2012年から）。
#: 2017年からと同じ検証データで比べ、2012年からのほうが当たったので、2026-09-30 に延ばした。
DEFAULT_TRAIN_FIRST_DAY = date(2012, 1, 1)


class TrainCommand:
    """``train``: 学習データを1回作り、券種ごと・3つの時点ごとに2つのモデルを学習して保存し、検証データでの当たり具合を出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "train", help="券種ごと・3つの時点（木曜・前日・当日）ごとに2つのモデルを学習して保存する", allow_abbrev=False,
        )
        parser.add_argument(
            "--config", type=Path, default=None,
            help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）",
        )
        parser.add_argument(
            "--bet", nargs="*", default=None, choices=[bet.label for bet in BetType], metavar="券種",
            help=f"学習する券種: {BET_CHOICES}（省略すると4つ全部）",
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
            builder = race_dataset_builder(con)
            training_data = builder.build_training_data(period)
        repositories = model_repositories(args.models)
        settings = HyperparameterSettings.load(args.config, defaults=DEFAULT_SETTINGS_PATH)
        tables: list[Table] = []
        for bet in self._bets(args):
            workflow = TrainingWorkflow(
                builder, period, repositories[bet], TIMINGS, DEFAULT_SETTINGS_PATH,
                member_types=CLASS_MEMBER_TYPES, evaluator=ClassModelEvaluator(),
            )
            labeled = training_data.with_label(bet.column_name)
            report = workflow.train(labeled, args.config)
            tables += ClassTrainingReportTables(report, UpsetLevel.labels(), bet.label).tables()
            tables += self._comparison_tables(bet, report, repositories[bet], settings)
        return tables

    def _comparison_tables(self, bet: BetType, report: TrainingReport, repository: ModelRepository,
                           settings: HyperparameterSettings) -> list[Table]:
        """検証データでの、基準との比べと使い方の線引きの表（設計書 16 の 3）。"""
        valid = report.split.valid
        thresholds = {
            timing: UpsetThresholdSummary().summarize(EnsembleModel(repository.load(timing)), valid.for_timing(timing))
            for timing in TIMINGS
        }
        return UpsetComparisonTables(
            bet, report.evaluations, ClassShareBaseline().evaluate(report.split, TIMINGS),
            UserRuleBaseline().evaluate(valid), thresholds, FavoriteOddsBaseline(settings).evaluate(report.split),
        ).tables()

    def _bets(self, args: argparse.Namespace) -> list[BetType]:
        """``--bet`` で渡された券種。渡されなければ4つ全部。"""
        if not args.bet:
            return list(BetType)
        return [BetType.parse(text) for text in args.bet]

    def _add_period_arguments(self, parser: argparse.ArgumentParser) -> None:
        """学習データの期間の区切り（設計書 08 の 4）。古い順に ウォームアップ → 学習 → 検証 → テスト。"""
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=None,
            help="ウォームアップ期間の最初の開催日。この日からの出走を近走と過去の荒れ率の計算にだけ使い、サンプルにしない"
                 "（省略すると、学習データの最初の日の前の年の1月1日）",
        )
        group.add_argument(
            "--train-from", type=date.fromisoformat, default=DEFAULT_TRAIN_FIRST_DAY,
            help=f"学習データの最初の開催日（既定: {DEFAULT_TRAIN_FIRST_DAY}。DB にある全部）",
        )
        group.add_argument(
            "--valid-from", type=date.fromisoformat, default=DEFAULT_VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {DEFAULT_VALID_FIRST_DAY}。これより前が学習データ）",
        )
        group.add_argument(
            "--test-from", type=date.fromisoformat, default=DEFAULT_TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {DEFAULT_TEST_FIRST_DAY}）",
        )
