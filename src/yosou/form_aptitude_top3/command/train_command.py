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
    TrainingData,
    TrainingPeriod,
)
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import ABILITY_TRAIN_FIRST_DAY, PoolFreeData, ability_dataset_builder, pool_dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import ABILITY_TIMINGS, FORM_TIMINGS, POOL_FREE_FOLDER
from .figure_cache_argument import FigureCacheArgument
from .yosou_name import YOSOU_NAME


class TrainCommand:
    """``train``: 時点ごとに2つのモデルを学習して保存し、検証データでの当たり具合を出す。

    時点によって材料が違う（設計書 07）。木曜・前日は馬の力の材料（2012年からの学習データ）、当日は今の材料に
    券種ごとのオッズから見た支持を足したもので学ぶ。当日は、券種のオッズが無いレースのために、支持を使わないモデルも
    学んで ``<置き場所>/券種オッズなし/`` に保存する。
    学習のあとに、複勝の見込みの倍率（今の材料の学習データの期間の払戻から決めたもの）も保存する（予測で複勝の期待値を出すため）。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "train", help="時点ごとに2つのモデルを学習して保存する", allow_abbrev=False,
        )
        parser.add_argument(
            "--config", type=Path, default=None,
            help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）",
        )
        self._add_period_arguments(parser)
        FigureCacheArgument().add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データを読む段だけ。学習は DB を閉じてから行い、ほかの道具を待たせない。"""
        form_period = TrainingPeriod.starting(
            args.train_from, args.valid_from, args.test_from, warmup_first_day=args.warmup_from,
        )
        ability_period = TrainingPeriod.starting(args.ability_train_from, args.valid_from, args.test_from)
        repository = ModelRepository(args.models, MEMBER_TYPES)
        with db.open_db(args.db) as con:
            form = TrainingWorkflow(pool_dataset_builder(con), form_period, repository, FORM_TIMINGS, DEFAULT_SETTINGS_PATH)
            ability = TrainingWorkflow(ability_dataset_builder(con, args.figure_cache), ability_period, repository, ABILITY_TIMINGS,
                                       DEFAULT_SETTINGS_PATH)
            form_data = form.read_training_data()
            ability_data = ability.read_training_data() if ABILITY_TIMINGS else None
        tables = self._form_tables(form, form_data, form_period, args)
        if ability_data is not None:
            tables += TrainingReportTables(ability.train(ability_data, args.config), "馬の力の材料").tables()
        return tables

    def _form_tables(self, form: TrainingWorkflow, form_data: TrainingData, period: TrainingPeriod,
                     args: argparse.Namespace) -> list[Table]:
        """今の材料のモデル（当日）と、券種のオッズが無いときの当日のモデルを学んで、結果の表を返す。"""
        report = form.train(form_data, args.config)
        pool_free = TrainingWorkflow(
            None, period, ModelRepository(args.models / POOL_FREE_FOLDER, MEMBER_TYPES), (PredictionTiming.RACE_DAY,),
            DEFAULT_SETTINGS_PATH,
        ).train(PoolFreeData().training(form_data), args.config)
        place_price = PlacePriceStep().run(report.split.train, args.models)
        return [*TrainingReportTables(report, "今の材料").tables(),
                *TrainingReportTables(pool_free, "券種オッズなし").tables(), place_price]

    def _add_period_arguments(self, parser: argparse.ArgumentParser) -> None:
        """学習データの期間の区切り（設計書 08 の 3）。古い順に ウォームアップ → 学習 → 検証 → テスト。"""
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=None,
            help="今の材料のウォームアップ期間の最初の開催日。この日からの出走を過去走の計算にだけ使い、サンプルにしない"
                 "（省略すると、学習データの最初の日の前の年の1月1日）",
        )
        group.add_argument(
            "--train-from", type=date.fromisoformat, default=DEFAULT_TRAIN_FIRST_DAY,
            help=f"今の材料（当日）の学習データの最初の開催日（既定: {DEFAULT_TRAIN_FIRST_DAY}）",
        )
        group.add_argument(
            "--ability-train-from", type=date.fromisoformat, default=ABILITY_TRAIN_FIRST_DAY,
            help=f"馬の力の材料（木曜・前日）の学習データの最初の開催日（既定: {ABILITY_TRAIN_FIRST_DAY}。"
                 "ウォームアップはその前の年の1月1日から）",
        )
        group.add_argument(
            "--valid-from", type=date.fromisoformat, default=DEFAULT_VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {DEFAULT_VALID_FIRST_DAY}。これより前が学習データ）",
        )
        group.add_argument(
            "--test-from", type=date.fromisoformat, default=DEFAULT_TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {DEFAULT_TEST_FIRST_DAY}）",
        )
