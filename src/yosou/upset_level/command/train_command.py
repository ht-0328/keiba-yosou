"""train: 学習する。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import ClassTrainingReportTables, CommonArguments
from yosou.shared.dataset import DEFAULT_TEST_FIRST_DAY, DEFAULT_VALID_FIRST_DAY, TrainingData, TrainingPeriod
from yosou.shared.evaluation import ClassModelEvaluator
from yosou.shared.ml_model import CLASS_MEMBER_TYPES
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import BET_CHOICES, BetType, UpsetLevel, race_dataset_builder
from ..evaluation import UserRuleBaseline, UserRuleResult
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import TIMINGS, model_repositories
from .yosou_name import YOSOU_NAME

#: 学習データの始まりの既定（設計書 08 の 4）。DB にある全部（2016年をウォームアップにして 2017年から）。
DEFAULT_TRAIN_FIRST_DAY = date(2017, 1, 1)


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
        tables: list[Table] = []
        for bet in self._bets(args):
            workflow = TrainingWorkflow(
                builder, period, repositories[bet], TIMINGS, DEFAULT_SETTINGS_PATH,
                member_types=CLASS_MEMBER_TYPES, evaluator=ClassModelEvaluator(),
            )
            labeled = training_data.with_label(bet.column_name)
            report = workflow.train(labeled, args.config)
            tables += ClassTrainingReportTables(report, UpsetLevel.labels(), bet.label).tables()
            tables.append(self._user_rule_table(bet, UserRuleBaseline().evaluate(report.split.valid)))
        return tables

    def _bets(self, args: argparse.Namespace) -> list[BetType]:
        """``--bet`` で渡された券種。渡されなければ4つ全部。"""
        if not args.bet:
            return list(BetType)
        return [BetType.parse(text) for text in args.bet]

    def _user_rule_table(self, bet: BetType, result: UserRuleResult) -> Table:
        """利用者の規則を基準にしたときの、検証データでの当たり具合（設計書 16 の 3）。"""
        return Table(
            ["レース数", "規則に当てはまる数", "当てはまったうち中荒れ以上の割合", "中荒れ以上のうち当てはまった割合", "中荒れ以上の割合"],
            [[result.rows, result.hits, self._rounded(result.precision), self._rounded(result.recall),
              self._rounded(result.base_rate)]],
            title=f"{bet.label}: 利用者の規則（1番人気 4.0倍以上かつ 2〜5番人気 10倍未満）を基準にしたとき",
            note="規則に当てはまるレースを「中荒れ以上」と予想したとみなした値。検証データで測る。",
        )

    def _rounded(self, value: float) -> float | None:
        if value != value:  # NaN
            return None
        return round(value, 3)

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
