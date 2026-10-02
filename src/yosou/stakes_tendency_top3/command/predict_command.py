"""predict: 1レース（重賞）を予測する。"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from 共通 import db, race
from 共通.render import Table

from yosou.form_aptitude_top3.command.figure_cache_argument import FigureCacheArgument
from yosou.shared.command import CommonArguments, PredictionTable
from yosou.shared.dataset import DatasetBuilder
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP3_RATE
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE, PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, PlacePriceRepository
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER
from yosou.shared.workflow import ModelSegments, SegmentedPrediction

from ..dataset import POOL_FREE_FOLDER, OddsInput, OddsResolver, ability_dataset_builder, race_day_dataset_builder
from ..feature import WIN_ODDS
from ..workflow import ABILITY_TIMINGS, PROBABILITY, PredictionWorkflow
from .yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レース（重賞）の出走馬ごとの「3着以内に入る確率」を出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "predict", help="1レース（重賞）の出走馬ごとの「3着以内に入る確率」を出す", allow_abbrev=False,
        )
        parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
        parser.add_argument("--date", help="開催日 YYYY-MM-DD（rid を省くとき）")
        parser.add_argument("--venue", help="競馬場の名前かコード（rid を省くとき）")
        parser.add_argument("--race", type=int, help="レース番号（rid を省くとき）")
        parser.add_argument(
            "--timing", type=PredictionTiming.parse, required=True,
            help="予測する時点: 木曜（thursday）・前日（day_before）・当日（race_day）",
        )
        parser.add_argument(
            "--odds", nargs="*", default=None, metavar="馬番:オッズ",
            help="利用者が見た単勝オッズ（例: --odds 3:2.4 7:5.1 や --odds 3:2.4,7:5.1）。前日と当日に使う。"
                 "省略すると、締め切り前のオッズか、元DB の単勝オッズ（終わったレースの確定オッズ）を使う",
        )
        FigureCacheArgument().add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        with db.open_db(args.db) as con:
            race_id = self._race_id(args, con)
            return [self.predict_table(con, race_id, args.timing, args.models, self._given_odds(args), args.figure_cache)]

    def predict_table(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming,
                      models: Path, given: OddsInput | None = None, figure_cache: Path = DEFAULT_FOLDER) -> Table:
        """開いてある元DB で1レース（重賞）を予測し、確率の高い順の表にする。

        ほかの道具も、同じ予測をこのメソッドで出せる。重賞でなければ ``ValueError``、
        学習済みのモデルが無ければ ``FileNotFoundError``。``figure_cache`` はスピード指数をとっておく場所。
        """
        workflow = PredictionWorkflow(
            self._dataset_builder(con, timing, figure_cache), SegmentedPrediction(ModelSegments(), models),
            OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(self._place_price(models)),
            pool_free=SegmentedPrediction(ModelSegments(), models / POOL_FREE_FOLDER),
        )
        prediction = workflow.run(race_id, timing, given)
        return PredictionTable(prediction, timing, PROBABILITY, self._extra_columns(prediction)).table()

    def _dataset_builder(self, con: duckdb.DuckDBPyConnection, timing: PredictionTiming, figure_cache: Path) -> DatasetBuilder:
        """その時点のモデルの材料の組み立て。木曜・前日は馬の力の材料＋K、当日は当日の材料＋K。"""
        if timing in ABILITY_TIMINGS:
            return ability_dataset_builder(con, figure_cache)
        return race_day_dataset_builder(con, figure_cache)

    def _given_odds(self, args: argparse.Namespace) -> OddsInput | None:
        """``--odds`` で渡されたオッズ。渡されなければ None。"""
        if not args.odds:
            return None
        return OddsInput.of(args.odds)

    def _extra_columns(self, prediction: pd.DataFrame) -> list[str]:
        """馬名のあとに出す列。前日・当日は単勝オッズ・オッズから見た3着以内率・複勝的中の確率・複勝の期待値
        （見込みの倍率を保存してあれば）を出し、木曜（オッズを使わない）は出さない。"""
        return [column for column in (WIN_ODDS, TOP3_RATE, PLACE_PROBABILITY, PLACE_VALUE) if column in prediction.columns]

    def _place_price(self, models: Path) -> PlacePriceEstimator | None:
        """学習のときに保存した複勝の見込みの倍率。無ければ None で、期待値は出さない。"""
        state = PlacePriceRepository(models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
