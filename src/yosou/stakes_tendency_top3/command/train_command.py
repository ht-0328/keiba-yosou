"""train: 学習する。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.form_aptitude_top3.command.figure_cache_argument import FigureCacheArgument
from yosou.shared.command import CommonArguments, PlacePriceStep, TrainingReportTables
from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import POOL_FREE_FOLDER, PoolFreeData, ability_dataset_builder, race_day_dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import ABILITY_TIMINGS, FORM_TIMINGS
from .retirement import RETIRED_NOTE
from .yosou_name import YOSOU_NAME

#: 学習データの期間の既定。重賞は年に約125レースしかないので、共通の既定（2021年8月〜）では行が足りず、
#: DB の全期間を使う（設計書 08 の 3・16 の 1）。ウォームアップは、学習の始まりの前の年の1月1日（2011-01-01）になる。
#: 木曜・前日（馬の力の材料）も当日も、同じ期間で学ぶ。
TRAIN_FIRST_DAY = date(2012, 1, 1)
VALID_FIRST_DAY = date(2025, 1, 1)
TEST_FIRST_DAY = date(2026, 1, 1)


class TrainCommand:
    """``train``: 3つの時点ごとに2つのモデルを学習して保存し、検証データでの当たり具合を出す。

    時点によって材料が違う（設計書 07。手本と同じ構成に K を足す）。木曜・前日は馬の力の材料と K、当日は当日の材料
    （A〜L・N・M）と K で学ぶ。当日は、券種のオッズが無いレースのために、N を使わないモデルも学んで
    ``<置き場所>/券種オッズなし/`` に保存する。学習のあとに、複勝の見込みの倍率（学習データの期間の払戻から決めたもの）も保存する。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "train", help="3つの時点ごとに2つのモデルを学習して保存する（引退。確かめ直し用）", allow_abbrev=False,
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
        period = TrainingPeriod.starting(
            args.train_from, args.valid_from, args.test_from, warmup_first_day=args.warmup_from,
        )
        repository = ModelRepository(args.models, MEMBER_TYPES)
        with db.open_db(args.db) as con:
            race_day = TrainingWorkflow(race_day_dataset_builder(con, args.figure_cache), period, repository, FORM_TIMINGS,
                                        DEFAULT_SETTINGS_PATH)
            ability = TrainingWorkflow(ability_dataset_builder(con, args.figure_cache), period, repository, ABILITY_TIMINGS,
                                       DEFAULT_SETTINGS_PATH)
            race_day_data = race_day.read_training_data()
            ability_data = ability.read_training_data()
        tables = self._race_day_tables(race_day, race_day_data, period, args)
        tables += TrainingReportTables(ability.train(ability_data, args.config), "馬の力の材料＋重賞の傾向").tables()
        tables[0].note = f"{RETIRED_NOTE} {tables[0].note}"
        return tables

    def _race_day_tables(self, race_day: TrainingWorkflow, data: TrainingData, period: TrainingPeriod,
                         args: argparse.Namespace) -> list[Table]:
        """当日のモデルと、券種のオッズが無いときの当日のモデルを学んで、結果の表を返す。"""
        report = race_day.train(data, args.config)
        pool_free = TrainingWorkflow(
            None, period, ModelRepository(args.models / POOL_FREE_FOLDER, MEMBER_TYPES), (PredictionTiming.RACE_DAY,),
            DEFAULT_SETTINGS_PATH,
        ).train(PoolFreeData().training(data), args.config)
        place_price = PlacePriceStep().run(report.split.train, args.models)
        return [*TrainingReportTables(report, "当日の材料＋重賞の傾向").tables(),
                *TrainingReportTables(pool_free, "券種オッズなし").tables(), place_price]

    def _add_period_arguments(self, parser: argparse.ArgumentParser) -> None:
        """学習データの期間の区切り（設計書 08 の 3）。古い順に ウォームアップ → 学習 → 検証 → テスト。"""
        group = parser.add_argument_group("学習データの期間")
        group.add_argument(
            "--warmup-from", type=date.fromisoformat, default=None,
            help="ウォームアップ期間の最初の開催日。この日からの出走を過去走の計算にだけ使い、サンプルにしない"
                 "（省略すると、学習データの最初の日の前の年の1月1日）",
        )
        group.add_argument(
            "--train-from", type=date.fromisoformat, default=TRAIN_FIRST_DAY,
            help=f"学習データの最初の開催日（既定: {TRAIN_FIRST_DAY}。重賞は少ないので全期間を使う。3つの時点とも同じ）",
        )
        group.add_argument(
            "--valid-from", type=date.fromisoformat, default=VALID_FIRST_DAY,
            help=f"検証データの最初の開催日（既定: {VALID_FIRST_DAY}。これより前が学習データ）",
        )
        group.add_argument(
            "--test-from", type=date.fromisoformat, default=TEST_FIRST_DAY,
            help=f"テストデータの最初の開催日（既定: {TEST_FIRST_DAY}）",
        )
