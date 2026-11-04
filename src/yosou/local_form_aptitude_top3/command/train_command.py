"""train: 学習する。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments, PlacePriceStep, TrainingReportTables
from yosou.shared.dataset import FinishPowerFreeData, PoolFreeData, TrainingData, TrainingPeriod, WinTargetData
from yosou.shared.evaluation import TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import TrainingWorkflow
from yosou.local_track_bias import LOCAL_TRACK_BIAS_FEATURES, LocalBiasHistory, TrackBiasMarker
from yosou.track_bias import BiasAttachment, BiasRunRepository

from ..dataset import local_dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import POOL_FREE_FOLDER, TIMING_LABELS, TIMINGS, WIN_FOLDER
from .period_arguments import PeriodArguments
from .yosou_name import YOSOU_NAME

#: 1着のモデルの表の題に付ける言葉。
_WIN_SUBJECT = "1着"


class TrainCommand:
    """``train``: 3つの時点ごとに2つのモデルを学習して保存し、検証データでの当たり具合を出す。

    学習データは1つ（``local_dataset_builder``。当日の全部の特徴量）で、時点ごとにその時点で使う列だけで学ぶ（設計書 07）。
    同じ学習データで、3着以内のモデル（Q を外す）と、目的変数を「1着」に・基準をオッズから見た勝率に持ち替えた1着のモデル
    （``WinTargetData``。Q は残す）を別々に学び、1着のモデルは ``<置き場所>/1着/`` に保存する（設計書 10）。
    当日は、券種のオッズが無いレースのために、N を外したモデルも学んで ``<置き場所>/券種オッズなし/`` に保存する。
    ``--track-bias`` を付けたときだけ、当日のモデル（3着以内・1着・券種オッズなし）を当日の馬場傾向（U。``yosou.local_track_bias``）を
    足した学習データで学び、置き場所に印（``TrackBiasMarker``）を書く（設計書 09 の U・15 の 11。本番のモデルは U なし。
    U は当日から分かる列なので、出馬表・前日のモデルには渡らない）。
    学習のあとに、複勝の見込みの倍率（学習データの期間の払戻から決めたもの）も保存する（予測で複勝の期待値を出すため）。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("train", help="時点ごとに2つのモデルを学習して保存する", allow_abbrev=False)
        parser.add_argument(
            "--config", type=Path, default=None, help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）",
        )
        parser.add_argument(
            "--timings", nargs="+", type=PredictionTiming.parse, default=None, metavar="時点",
            help="学習する時点だけに絞る（出馬表 前日 当日。省略すると全部）。1つの時点のモデルだけ学び直すときに使う",
        )
        parser.add_argument(
            "--track-bias", action="store_true",
            help="当日のモデルに当日の馬場傾向（U）を足して学ぶ（本番は付けない。設計書 15 の 11）。置き場所に印 当日の馬場傾向.json を書く",
        )
        PeriodArguments().add_to(parser)
        CommonArguments(YOSOU_NAME, db.LOCAL).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データと、当日の馬場傾向の元（過去の全出走）を読む段だけ。学習は DB を閉じてから行い、ほかの道具を待たせない。"""
        period = PeriodArguments().period_of(args)
        timings = tuple(args.timings) if args.timings else TIMINGS
        race_day = PredictionTiming.RACE_DAY
        with_bias = args.track_bias and race_day in timings
        with db.open_db(args.db, default=db.LOCAL) as con:
            data = local_dataset_builder(con).build_training_data(period)
            runs = BiasRunRepository(con).read(period.warmup_first_day) if with_bias else None
        if runs is not None:
            data = BiasAttachment(LOCAL_TRACK_BIAS_FEATURES).apply(data, LocalBiasHistory().of(race_day, runs))
            TrackBiasMarker(args.models).save()
        tables, report = self._both(data, period, args.models, timings, "今の材料", args.config)
        if race_day in timings:
            pool_free, _ = self._both(PoolFreeData().training(data), period, args.models / POOL_FREE_FOLDER,
                                      (race_day,), "券種オッズなし", args.config)
            tables = [*tables, *pool_free]
        return [*tables, PlacePriceStep().run(report.split.train, args.models)]

    def _both(self, data: TrainingData, period: TrainingPeriod, root: Path, timings: tuple[PredictionTiming, ...],
              subject: str, config: Path | None) -> tuple[list[Table], TrainingReport]:
        """同じ学習データで、3着以内のモデル（``root``。Q は外す）と1着のモデル（``root/1着``。Q も使う）を学んで保存する。結果の表と、3着以内の学習の結果を返す。"""
        top3 = self._workflow(period, root, timings).train(FinishPowerFreeData().training(data), config)
        win = self._workflow(period, root / WIN_FOLDER, timings).train(WinTargetData().training(data), config)
        tables = [*TrainingReportTables(top3, subject, TIMING_LABELS).tables(),
                  *TrainingReportTables(win, f"{_WIN_SUBJECT}: {subject}", TIMING_LABELS).tables()]
        return tables, top3

    def _workflow(self, period: TrainingPeriod, root: Path, timings: tuple[PredictionTiming, ...]) -> TrainingWorkflow:
        """読んだ学習データで学ぶだけの学習の流れ（学習データは作らない）。"""
        return TrainingWorkflow(None, period, ModelRepository(root, MEMBER_TYPES), timings, DEFAULT_SETTINGS_PATH)
