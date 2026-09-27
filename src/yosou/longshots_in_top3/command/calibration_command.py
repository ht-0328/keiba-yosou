"""calibration: 保存したモデルの確率のずれを測る。"""

from __future__ import annotations

import argparse

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CalibrationReportTables, CommonArguments
from yosou.shared.dataset import PeriodSplitter
from yosou.shared.place_value import PlaceExpectedValue, PlacePriceEstimator
from yosou.shared.repository import PlacePriceRepository
from yosou.shared.workflow import CalibrationCheck, SegmentedHoldoutPrediction

from ..dataset import dataset_builder
from ..workflow import SEGMENTS, TIMINGS
from .period_arguments import PeriodArguments
from .yosou_name import YOSOU_NAME


class CalibrationCommand:
    """``calibration``: 保存したモデルが出す「3着以内に入る確率」が、実際に3着以内に入った割合と合っているか（確率のずれ）と、
    その確率から出した複勝の期待値が、実際の回収率と合っているかを、学習に使っていない期間（検証・テスト）で測る
    （設計書 16 の 4）。

    学習のときと同じ期間の区切りを渡す（省略すると既定の区切り）。元DB を開くのは学習データを読む段だけ。
    """

    def __init__(self) -> None:
        self._period_arguments = PeriodArguments()

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "calibration", allow_abbrev=False,
            help="保存したモデルの確率のずれと期待値の当たり具合を、検証・テストの期間で測る",
        )
        self._period_arguments.add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        period = self._period_arguments.period(args)
        with db.open_db(args.db) as con:
            training_data = dataset_builder(con).build_training_data(period)
        split = PeriodSplitter(period).split(training_data)
        check = CalibrationCheck(SEGMENTS, SegmentedHoldoutPrediction(SEGMENTS, args.models),
                                 self._place_value(args), TIMINGS)
        return CalibrationReportTables(check.run(split)).tables()

    def _place_value(self, args: argparse.Namespace) -> PlaceExpectedValue | None:
        """学習のときに保存した複勝の見込みの倍率。無ければ None で、期待値は測らない。"""
        state = PlacePriceRepository(args.models).load()
        return PlaceExpectedValue(PlacePriceEstimator.from_state(state)) if state is not None else None
