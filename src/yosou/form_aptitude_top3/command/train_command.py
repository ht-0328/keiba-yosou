"""train: 学習する。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

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
from yosou.race_development.workflow import PaceForecastHistory
from yosou.shared.evaluation import TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import (
    ABILITY_TRAIN_FIRST_DAY,
    PaceAttachment,
    PoolFreeData,
    WinTargetData,
    ability_dataset_builder,
    race_day_dataset_builder,
)
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import ABILITY_TIMINGS, FORM_TIMINGS, PACE_TIMINGS, POOL_FREE_FOLDER, WIN_FOLDER
from .development_root_argument import DevelopmentRootArgument
from .figure_cache_argument import FigureCacheArgument
from .yosou_name import YOSOU_NAME

#: 1着のモデルの表の題に付ける言葉。
_WIN_SUBJECT = "1着"


class TrainCommand:
    """``train``: 時点ごとに2つのモデルを学習して保存し、検証データでの当たり具合を出す。

    時点によって材料が違う（設計書 07）。木曜・前日は馬の力の材料（2012年からの学習データ）、当日は今の材料に
    券種ごとのオッズから見た支持と馬の力の材料を足したもので学ぶ。当日は、券種のオッズが無いレースのために、支持を使わないモデルも
    学んで ``<置き場所>/券種オッズなし/`` に保存する。
    展開の予想の結果（P）を採用した時点（``PACE_TIMINGS``。木曜）は、馬の力の材料に、予想「展開から着順を予想」の年ごとの確かめの
    予測から作った P を足して学ぶ（設計書 15 の 13）。そのため、その時点だけ別に学ぶ。
    どの学習データでも、3着以内のモデルと、目的変数を「1着」に・基準をオッズから見た勝率に持ち替えた1着のモデル（``WinTargetData``）を
    別々に学び、1着のモデルは ``<置き場所>/1着/`` に保存する（設計書 10・15 の 14）。
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
        DevelopmentRootArgument().add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データを読む段だけ。学習は DB を閉じてから行い、ほかの道具を待たせない。"""
        form_period = TrainingPeriod.starting(
            args.train_from, args.valid_from, args.test_from, warmup_first_day=args.warmup_from,
        )
        ability_period = TrainingPeriod.starting(args.ability_train_from, args.valid_from, args.test_from)
        history = PaceForecastHistory(args.development_root)
        paces = {timing: history.read(timing) for timing in PACE_TIMINGS}
        with db.open_db(args.db) as con:
            form_data = race_day_dataset_builder(con, args.figure_cache).build_training_data(form_period)
            ability_data = (ability_dataset_builder(con, args.figure_cache).build_training_data(ability_period)
                            if ABILITY_TIMINGS else None)
        tables = self._form_tables(form_data, form_period, args)
        if ability_data is not None:
            tables += self._ability_tables(ability_data, ability_period, paces, args)
        return tables

    def _form_tables(self, data: TrainingData, period: TrainingPeriod, args: argparse.Namespace) -> list[Table]:
        """今の材料のモデル（当日）と、券種のオッズが無いときの当日のモデルを学んで、結果の表を返す。"""
        tables, report = self._both(data, period, args.models, FORM_TIMINGS, "今の材料", args.config)
        pool_free, _ = self._both(PoolFreeData().training(data), period, args.models / POOL_FREE_FOLDER,
                                  (PredictionTiming.RACE_DAY,), "券種オッズなし", args.config)
        return [*tables, *pool_free, PlacePriceStep().run(report.split.train, args.models)]

    def _ability_tables(self, data: TrainingData, period: TrainingPeriod,
                        paces: dict[PredictionTiming, pd.DataFrame], args: argparse.Namespace) -> list[Table]:
        """馬の力の材料のモデル（木曜・前日）を学んで、結果の表を返す。P を採用した時点は、その時点の展開の予測から作った P を
        足した学習データで、時点ごとに学ぶ（``paces`` は 時点 → 展開の予想の元の予測の表）。"""
        plain = tuple(timing for timing in ABILITY_TIMINGS if timing not in paces)
        tables = self._both(data, period, args.models, plain, "馬の力の材料", args.config)[0] if plain else []
        for timing in ABILITY_TIMINGS:
            if timing in paces:
                tables += self._both(PaceAttachment().apply(data, paces[timing]), period, args.models, (timing,),
                                     f"馬の力の材料 ＋ 展開の予想（{timing.label}）", args.config)[0]
        return tables

    def _both(self, data: TrainingData, period: TrainingPeriod, root: Path, timings: tuple[PredictionTiming, ...],
              subject: str, config: Path | None) -> tuple[list[Table], TrainingReport]:
        """同じ学習データで、3着以内のモデル（``root``）と1着のモデル（``root/1着``）を学んで保存する。結果の表と、3着以内の学習の結果を返す。"""
        top3 = self._workflow(period, root, timings).train(data, config)
        win = self._workflow(period, root / WIN_FOLDER, timings).train(WinTargetData().training(data), config)
        tables = [*TrainingReportTables(top3, subject).tables(), *TrainingReportTables(win, f"{_WIN_SUBJECT}: {subject}").tables()]
        return tables, top3

    def _workflow(self, period: TrainingPeriod, root: Path, timings: tuple[PredictionTiming, ...]) -> TrainingWorkflow:
        """読んだ学習データで学ぶだけの学習の流れ（学習データは作らない）。"""
        return TrainingWorkflow(None, period, ModelRepository(root, MEMBER_TYPES), timings, DEFAULT_SETTINGS_PATH)

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
