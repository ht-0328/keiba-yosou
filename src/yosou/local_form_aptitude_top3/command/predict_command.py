"""predict: 1レースを予測する。"""

from __future__ import annotations

import argparse

import duckdb
import pandas as pd

from 共通 import db, race
from 共通.render import Table

from yosou.shared.command import CommonArguments, PredictionTable
from yosou.shared.dataset import OddsInput, OddsResolver
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.group import WIN_ODDS
from yosou.shared.feature.odds import TOP3_RATE
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE, PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, PlacePriceRepository
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.win_value import WIN_VALUE
from yosou.shared.workflow import (
    PROBABILITY,
    WIN_PROBABILITY,
    WIN_PROBABILITY_MEMBER,
    DataAttachment,
    ModelSegments,
    PredictionWorkflow,
    SegmentedPrediction,
)
from yosou.local_track_bias import LOCAL_TRACK_BIAS_FEATURES, LocalFrontForecast, TrackBiasMarker, local_bias_cache_folder_beside
from yosou.track_bias import BiasAttachment, PriorSlopeTableStore, RaceBiasAttacher

from ..dataset import local_dataset_builder
from ..workflow import POOL_FREE_FOLDER, TIMING_LABELS, WIN_FOLDER
from .yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レースの出走馬ごとの「3着以内に入る確率」と「1着になる確率」（と、前日・当日は複勝・単勝の期待値）を出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "predict", help="1レースの出走馬ごとの「3着以内に入る確率」と「1着になる確率」を出す", allow_abbrev=False,
        )
        parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
        parser.add_argument("--date", help="開催日 YYYY-MM-DD（rid を省くとき）")
        parser.add_argument("--venue", help="競馬場の名前かコード（rid を省くとき。大井・名古屋 など、または 30〜61）")
        parser.add_argument("--race", type=int, help="レース番号（rid を省くとき）")
        parser.add_argument(
            "--timing", type=PredictionTiming.parse, required=True,
            help="予測する時点: 出馬表（thursday）・前日（day_before）・当日（race_day）",
        )
        parser.add_argument(
            "--odds", nargs="*", default=None, metavar="馬番:オッズ",
            help="利用者が見た単勝オッズ（例: --odds 3:2.4 7:5.1 や --odds 3:2.4,7:5.1）。前日と当日に使う。"
                 "省略すると、締め切り前のオッズか、元DB の単勝オッズ（終わったレースの確定オッズ）を使う",
        )
        CommonArguments(YOSOU_NAME, db.LOCAL).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        with db.open_db(args.db, default=db.LOCAL) as con:
            return self.tables(con, args)

    def tables(self, con: duckdb.DuckDBPyConnection, args: argparse.Namespace) -> list[Table]:
        """開いてある接続で予測する。同じ接続で続けて別の予想（発走前の通知の荒れ具合）を出すと、事実表を作り直さずに済む。"""
        race_id = self._race_id(args, con)
        extras = self._extras(con, args)
        workflow = PredictionWorkflow(
            local_dataset_builder(con), SegmentedPrediction(ModelSegments(), args.models),
            OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(self._place_price(args)),
            pool_free=SegmentedPrediction(ModelSegments(), args.models / POOL_FREE_FOLDER),
            win_predictor=SegmentedPrediction(ModelSegments(), args.models / WIN_FOLDER),
            win_pool_free=SegmentedPrediction(ModelSegments(), args.models / POOL_FREE_FOLDER / WIN_FOLDER),
            extras=extras, win_extras=extras,
        )
        prediction = workflow.run(race_id, args.timing, self._given_odds(args))
        table = PredictionTable(prediction, args.timing, PROBABILITY, self._extra_columns(prediction),
                                timing_label=TIMING_LABELS[args.timing])
        return [table.table()]

    def _extras(self, con: duckdb.DuckDBPyConnection, args: argparse.Namespace) -> list[DataAttachment]:
        """当日で、``train --track-bias`` で学んだモデル（置き場所に ``TrackBiasMarker`` の印がある）のときだけ、当日の馬場傾向（U）を予測用データに足す
        （設計書 15 の 11。本番のモデルは U なしなので足さない）。ほかの時点は無し。
        レースごとの傾きと過去の傾きの表は、モデルの置き場所の2つ上の ``地方の当日の馬場傾向/cache/`` にとっておく（元DB が変わったら作り直す）。"""
        if args.timing is not PredictionTiming.RACE_DAY or not TrackBiasMarker(args.models).exists():
            return []
        slopes, table = PriorSlopeTableStore(local_bias_cache_folder_beside(args.models)).load(con, args.db)
        attacher = RaceBiasAttacher(con, LocalFrontForecast().run, slopes, table, BiasAttachment(LOCAL_TRACK_BIAS_FEATURES))
        return [attacher.attach]

    def _given_odds(self, args: argparse.Namespace) -> OddsInput | None:
        """``--odds`` で渡されたオッズ。渡されなければ None。"""
        if not args.odds:
            return None
        return OddsInput.of(args.odds)

    def _extra_columns(self, prediction: pd.DataFrame) -> list[str]:
        """馬名のあとに出す列。前日・当日は単勝オッズ・オッズから見た3着以内率・複勝的中の確率・複勝の期待値
        （見込みの倍率を保存してあれば）・1着になる確率（平均と、モデルごと）・単勝の期待値を出し、出馬表（オッズを使わない）は1着になる確率だけ。
        モデルごとの1着になる確率は、地方の推奨買目（1着・2着・3着を分けて市場に合わせる）の材料。"""
        members = [WIN_PROBABILITY_MEMBER.format(member=model_type.name) for model_type in MEMBER_TYPES]
        shown = (WIN_ODDS, TOP3_RATE, PLACE_PROBABILITY, PLACE_VALUE, WIN_PROBABILITY, *members, WIN_VALUE)
        return [column for column in shown if column in prediction.columns]

    def _place_price(self, args: argparse.Namespace) -> PlacePriceEstimator | None:
        """学習のときに保存した複勝の見込みの倍率。無ければ None で、期待値は出さない。"""
        state = PlacePriceRepository(args.models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
