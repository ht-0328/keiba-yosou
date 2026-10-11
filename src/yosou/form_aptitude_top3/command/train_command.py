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
from yosou.ability_score import ABILITY_SCORE_NAMES, AbilityScoreAttachment, AbilityScoreFreeData
from yosou.development_score import (
    DEVELOPMENT_SCORE_NAMES,
    AdvantageRuns,
    DevelopmentRunRepository,
    DevelopmentScoreFreeData,
    ScoreAttachment,
    ScoreHistory,
)
from yosou.race_development.workflow import PaceForecastHistory
from yosou.track_bias import TRACK_BIAS_NAMES, BiasAttachment, BiasHistory, BiasRunRepository, TrackBiasFreeData
from yosou.weight_table import WEIGHT_DISCOUNT_NAMES, WeightDiscountFreeData, WeightRunRepository, WeightRuns, YearlyWeightDiscount
from yosou.shared.evaluation import TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow

from ..dataset import (
    ABILITY_TRAIN_FIRST_DAY,
    FinishPowerFreeData,
    PaceAttachment,
    PoolFreeData,
    WinTargetData,
    ability_dataset_builder,
    race_day_dataset_builder,
)
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import (
    ABILITY_SCORE_TIMINGS,
    TIMINGS,
    ABILITY_SCORE_TOP3_TIMINGS,
    ABILITY_SCORE_WIN_TIMINGS,
    ABILITY_TIMINGS,
    FORM_TIMINGS,
    PACE_TIMINGS,
    POOL_FREE_FOLDER,
    SCORE_TIMINGS,
    SCORE_TOP3_TIMINGS,
    SCORE_WIN_TIMINGS,
    TRACK_BIAS_TIMINGS,
    TRACK_BIAS_TOP3_TIMINGS,
    TRACK_BIAS_WIN_TIMINGS,
    WEIGHT_DISCOUNT_TIMINGS,
    WEIGHT_DISCOUNT_TOP3_TIMINGS,
    WEIGHT_DISCOUNT_WIN_TIMINGS,
    WIN_FOLDER,
)
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
    予測から作った P を足して学ぶ（設計書 15 の 13）。展開スコア（S）を採用した時点（``SCORE_TIMINGS``。前日）は、同じ予測と、
    元DB の全出走から年ごとに作る表 G で出した S を足して学ぶ（設計書 15 の 17）。S を使うのは、3着以内のモデルは ``SCORE_TOP3_TIMINGS``、
    1着のモデルは ``SCORE_WIN_TIMINGS`` の時点だけで、使わないモデルには ``DevelopmentScoreFreeData`` で外して渡す。
    能力スコア（T）を採用した時点（``ABILITY_SCORE_TIMINGS``）も同じ形で、学習データの能力指数と斤量から T を足して学び
    （設計書 15 の 18）、使わないモデルには ``AbilityScoreFreeData`` で外して渡す。
    トラックバイアスの補正（U）を採用した時点（``TRACK_BIAS_TIMINGS``）も同じ形で、元DB の全出走から出したレースごとの傾きと、
    その時点の展開の年ごとの確かめの予測④で作った U を足して学び（設計書 15 の 19）、使わないモデルには ``TrackBiasFreeData`` で外して渡す。
    馬体重の表の割引（V）を採用した時点（``WEIGHT_DISCOUNT_TIMINGS``。当日だけ）も同じ形で、元DB の全出走から年ごとに作る表 W で
    引いた V を足して学び（設計書 15 の 20）、使わないモデルには ``WeightDiscountFreeData`` で外して渡す。
    どの学習データでも、3着以内のモデルと、目的変数を「1着」に・基準をオッズから見た勝率に持ち替えた1着のモデル（``WinTargetData``）を
    別々に学び、1着のモデルは ``<置き場所>/1着/`` に保存する（設計書 10・15 の 14）。当日の学習データにある勝ち切る材料（Q）は
    1着のモデルだけが使い、3着以内のモデルには ``FinishPowerFreeData`` で外して渡す（設計書 15 の 15）。
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
        parser.add_argument(
            "--timings", nargs="+", type=PredictionTiming.parse, default=None, metavar="時点",
            help="学習する時点だけに絞る（木曜 前日 当日。省略すると全部）。1つの時点のモデルだけ学び直すときに使う",
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
        chosen = tuple(args.timings) if args.timings else TIMINGS
        form_timings = tuple(timing for timing in FORM_TIMINGS if timing in chosen)
        ability_timings = tuple(timing for timing in ABILITY_TIMINGS if timing in chosen)
        history = PaceForecastHistory(args.development_root)
        paces = {timing: history.read(timing) for timing in PACE_TIMINGS if timing in chosen}
        score_timings = tuple(timing for timing in SCORE_TIMINGS if timing in chosen)
        bias_timings = tuple(timing for timing in TRACK_BIAS_TIMINGS if timing in chosen)
        with db.open_db(args.db) as con:
            form_data = race_day_dataset_builder(con, args.figure_cache).build_training_data(form_period) if form_timings else None
            ability_data = (ability_dataset_builder(con, args.figure_cache).build_training_data(ability_period)
                            if ability_timings else None)
            prepared = AdvantageRuns().build(DevelopmentRunRepository(con).read()) if score_timings else None
            bias_runs = BiasRunRepository(con).read() if bias_timings else None
            weight_runs = WeightRuns().build(WeightRunRepository(con).read()) if WEIGHT_DISCOUNT_TIMINGS and form_timings else None
        scores = {timing: ScoreHistory(args.development_root).of(timing, prepared) for timing in score_timings}
        biases = {timing: BiasHistory(args.development_root).of(timing, bias_runs) for timing in bias_timings}
        tables = self._form_tables(form_data, form_period, scores, biases, weight_runs, args) if form_data is not None else []
        if ability_data is not None:
            tables += self._ability_tables(ability_data, ability_period, paces, scores, biases, args, ability_timings)
        return tables

    def _form_tables(self, data: TrainingData, period: TrainingPeriod, scores: dict[PredictionTiming, pd.DataFrame],
                     biases: dict[PredictionTiming, pd.DataFrame], weight_runs: pd.DataFrame | None, args: argparse.Namespace) -> list[Table]:
        """今の材料のモデル（当日）と、券種のオッズが無いときの当日のモデルを学んで、結果の表を返す。S・T・U・V を採用した時点（当日）なら、
        学習データに S・T・U・V を足してから学ぶ（使わないモデルには ``_both`` が外して渡す）。``weight_runs`` は表 W の材料。"""
        race_day = PredictionTiming.RACE_DAY
        if race_day in scores:
            data = ScoreAttachment().apply(data, scores[race_day])
        if race_day in ABILITY_SCORE_TIMINGS:
            data = AbilityScoreAttachment().apply(data)
        if race_day in biases:
            data = BiasAttachment().apply(data, biases[race_day])
        if race_day in WEIGHT_DISCOUNT_TIMINGS and weight_runs is not None:
            data = YearlyWeightDiscount().apply(data, weight_runs)
        tables, report = self._both(data, period, args.models, FORM_TIMINGS, "今の材料", args.config)
        pool_free, _ = self._both(PoolFreeData().training(data), period, args.models / POOL_FREE_FOLDER,
                                  (race_day,), "券種オッズなし", args.config)
        return [*tables, *pool_free, PlacePriceStep().run(report.split.train, args.models)]

    def _ability_tables(self, data: TrainingData, period: TrainingPeriod, paces: dict[PredictionTiming, pd.DataFrame],
                        scores: dict[PredictionTiming, pd.DataFrame], biases: dict[PredictionTiming, pd.DataFrame],
                        args: argparse.Namespace, timings: tuple[PredictionTiming, ...] = ABILITY_TIMINGS) -> list[Table]:
        """馬の力の材料のモデル（木曜・前日のうち ``timings``）を学んで、結果の表を返す。P・S・T・U を採用した時点は、その時点の展開の予測から作った P・S・U と、
        能力指数と斤量から作った T を足した学習データで、時点ごとに学ぶ（``paces`` は 時点 → 展開の予想の元の予測の表、``scores`` は
        時点 → 展開スコアの表、``biases`` は 時点 → バイアスの補正の表）。"""
        plain = tuple(timing for timing in timings
                      if timing not in paces and timing not in scores and timing not in ABILITY_SCORE_TIMINGS and timing not in biases)
        tables = self._both(data, period, args.models, plain, "馬の力の材料", args.config)[0] if plain else []
        for timing in timings:
            if timing in plain:
                continue
            attached, subject = data, "馬の力の材料"
            if timing in paces:
                attached, subject = PaceAttachment().apply(attached, paces[timing]), f"{subject} ＋ 展開の予想（{timing.label}）"
            if timing in scores:
                attached = ScoreAttachment().apply(attached, scores[timing])
            if timing in ABILITY_SCORE_TIMINGS:
                attached = AbilityScoreAttachment().apply(attached)
            if timing in biases:
                attached = BiasAttachment().apply(attached, biases[timing])
            tables += self._both(attached, period, args.models, (timing,), subject, args.config)[0]
        return tables

    def _both(self, data: TrainingData, period: TrainingPeriod, root: Path, timings: tuple[PredictionTiming, ...],
              subject: str, config: Path | None) -> tuple[list[Table], TrainingReport]:
        """同じ学習データで、3着以内のモデル（``root``。Q は外す）と1着のモデル（``root/1着``。Q も使う）を学んで保存する。
        S・T・U は、その時点で採用したモデル（3着以内は ``SCORE_TOP3_TIMINGS``・``ABILITY_SCORE_TOP3_TIMINGS``・``TRACK_BIAS_TOP3_TIMINGS``、
        1着は ``SCORE_WIN_TIMINGS``・``ABILITY_SCORE_WIN_TIMINGS``・``TRACK_BIAS_WIN_TIMINGS``）にだけ渡し、ほかは外す。
        結果の表（題に S・T・U の有無を添える）と、3着以内の学習の結果を返す。"""
        top3_data = self._kept(data, timings, SCORE_TOP3_TIMINGS, ABILITY_SCORE_TOP3_TIMINGS, TRACK_BIAS_TOP3_TIMINGS, WEIGHT_DISCOUNT_TOP3_TIMINGS)
        win_data = self._kept(data, timings, SCORE_WIN_TIMINGS, ABILITY_SCORE_WIN_TIMINGS, TRACK_BIAS_WIN_TIMINGS, WEIGHT_DISCOUNT_WIN_TIMINGS)
        top3 = self._workflow(period, root, timings).train(FinishPowerFreeData().training(top3_data), config)
        win = self._workflow(period, root / WIN_FOLDER, timings).train(WinTargetData().training(win_data), config)
        tables = [*TrainingReportTables(top3, self._subject(subject, top3_data)).tables(),
                  *TrainingReportTables(win, f"{_WIN_SUBJECT}: {self._subject(subject, win_data)}").tables()]
        return tables, top3

    def _kept(self, data: TrainingData, timings: tuple[PredictionTiming, ...], score_timings: tuple[PredictionTiming, ...],
              ability_score_timings: tuple[PredictionTiming, ...], track_bias_timings: tuple[PredictionTiming, ...],
              weight_discount_timings: tuple[PredictionTiming, ...]) -> TrainingData:
        """そのモデルが使う材料だけ残した学習データ（S は ``score_timings``、T は ``ability_score_timings``、U は ``track_bias_timings``、
        V は ``weight_discount_timings`` の時点のモデルだけが使う）。"""
        if not any(timing in score_timings for timing in timings):
            data = DevelopmentScoreFreeData().training(data)
        if not any(timing in ability_score_timings for timing in timings):
            data = AbilityScoreFreeData().training(data)
        if not any(timing in track_bias_timings for timing in timings):
            data = TrackBiasFreeData().training(data)
        if not any(timing in weight_discount_timings for timing in timings):
            data = WeightDiscountFreeData().training(data)
        return data

    def _subject(self, subject: str, data: TrainingData) -> str:
        """表の題。学習データに S が入っていれば「＋ 展開スコア」、T なら「＋ 能力スコア」、U なら「＋ トラックバイアス」、V なら「＋ 馬体重の表」を添える。"""
        for names, label in ((DEVELOPMENT_SCORE_NAMES, "展開スコア"), (ABILITY_SCORE_NAMES, "能力スコア"), (TRACK_BIAS_NAMES, "トラックバイアス"),
                             (WEIGHT_DISCOUNT_NAMES, "馬体重の表")):
            if any(name in data.features.columns for name in names):
                subject = f"{subject} ＋ {label}"
        return subject

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
