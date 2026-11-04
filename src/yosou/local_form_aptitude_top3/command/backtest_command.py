"""backtest: テスト期間の確かめ。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import BacktestReportTables, CommonArguments
from yosou.shared.feature import PredictionTiming
from yosou.shared.workflow import BacktestWorkflow
from yosou.local_track_bias import LOCAL_TRACK_BIAS_FEATURES, LocalBiasHistory, TrackBiasMarker
from yosou.track_bias import BiasAttachment, BiasRunRepository

from ..dataset import local_dataset_builder
from ..workflow import DEFAULT_PREDICTIONS_DIR, POOL_FREE_FOLDER, TIMING_LABELS, TIMINGS, WIN_FOLDER
from .period_arguments import PeriodArguments
from .yosou_name import YOSOU_NAME


class BacktestCommand:
    """``backtest``: 保存したモデルで、テスト期間（``--test-from`` 以降、DB にある最後の日まで）の全レースを予測し直し、
    当たり具合（モデル2つ・平均）を市場の確率と同じ指標で比べ、道具「印の成績」が読む予測の表を書く（設計書 16 の 4）。

    学習データの作り方と期間の引数は ``train`` と同じ。``train --track-bias`` で学んだモデル（置き場所に ``TrackBiasMarker`` の印がある）のときだけ、
    当日の馬場傾向 U も同じく足す。``train`` と同じ期間で学んだモデル（``--models``）を使うこと。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("backtest", help="保存したモデルでテスト期間を予測し直し、市場の確率と比べる", allow_abbrev=False)
        parser.add_argument(
            "--predictions", type=Path, default=DEFAULT_PREDICTIONS_DIR,
            help=f"予測の表を書く場所（既定: reports/{YOSOU_NAME}/predictions。時点ごとに <時点>.pkl と <時点>-1着.pkl）",
        )
        parser.add_argument(
            "--timings", nargs="+", type=PredictionTiming.parse, default=None, metavar="時点",
            help="確かめる時点だけに絞る（出馬表 前日 当日。省略すると全部）",
        )
        PeriodArguments().add_to(parser)
        CommonArguments(YOSOU_NAME, db.LOCAL).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データを読む段だけ。予測は DB を閉じてから行う。"""
        period = PeriodArguments().period_of(args)
        timings = tuple(args.timings) if args.timings else TIMINGS
        race_day = PredictionTiming.RACE_DAY
        with_bias = race_day in timings and TrackBiasMarker(args.models).exists()
        with db.open_db(args.db, default=db.LOCAL) as con:
            data = local_dataset_builder(con).build_training_data(period)
            runs = BiasRunRepository(con).read(period.warmup_first_day) if with_bias else None
        if runs is not None:
            data = BiasAttachment(LOCAL_TRACK_BIAS_FEATURES).apply(data, LocalBiasHistory().of(race_day, runs))
        workflow = BacktestWorkflow(args.models, timings, args.predictions, pool_free_folder=POOL_FREE_FOLDER, win_folder=WIN_FOLDER)
        return BacktestReportTables(workflow.run(data, period), TIMING_LABELS).tables()
