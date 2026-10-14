"""predict: 1レースを予測する。"""

from __future__ import annotations

import argparse

import duckdb
import pandas as pd

from 共通 import db, race
from 共通.render import Table

from yosou.shared.command import CommonArguments, FigureCacheArgument, PredictionTable
from yosou.race_development.workflow import DevelopmentPaceWorkflow
from yosou.shared.dataset import DatasetBuilder
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP3_RATE
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE, PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, PlacePriceRepository
from yosou.shared.win_value import WIN_VALUE
from yosou.shared.workflow import ModelSegments, SegmentedPrediction

from ..dataset import OddsInput, OddsResolver, ability_dataset_builder, race_day_dataset_builder
from ..feature import WIN_ODDS
from ..workflow import (
    ABILITY_SCORE_TOP3_TIMINGS,
    ABILITY_SCORE_WIN_TIMINGS,
    ABILITY_TIMINGS,
    PACE_TIMINGS,
    POOL_FREE_FOLDER,
    PROBABILITY,
    SCORE_TOP3_TIMINGS,
    SCORE_WIN_TIMINGS,
    TRACK_BIAS_TOP3_TIMINGS,
    TRACK_BIAS_WIN_TIMINGS,
    WEIGHT_DISCOUNT_TOP3_TIMINGS,
    WEIGHT_DISCOUNT_WIN_TIMINGS,
    WIN_FOLDER,
    WIN_PROBABILITY,
    DataAttachment,
    PaceSource,
    PredictionWorkflow,
)
from .development_root_argument import DevelopmentRootArgument
from .material_attachers import MaterialAttachers
from .yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レースの出走馬ごとの「3着以内に入る確率」と「1着になる確率」（と、前日・当日は複勝・単勝の期待値）を出す。

    ``yosou_name`` はモデルの既定の置き場所（``reports/<予想の名前>/models``）を決める。同じ材料・同じ列で学んだ別の予想
    （荒れる前提で着順を予想。``yosou.upset_premise``）が、自分の置き場所のモデルで予測するために渡す。
    """

    def __init__(self, yosou_name: str = YOSOU_NAME) -> None:
        self._yosou_name = yosou_name

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "predict", help="1レースの出走馬ごとの「3着以内に入る確率」と「1着になる確率」を出す", allow_abbrev=False,
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
        DevelopmentRootArgument().add_to(parser)
        CommonArguments(self._yosou_name).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        with db.open_db(args.db) as con:
            race_id = self._race_id(args, con)
            attachers = MaterialAttachers(con, args.development_root)
            workflow = PredictionWorkflow(
                self._dataset_builder(con, args), SegmentedPrediction(ModelSegments(), args.models),
                OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(self._place_price(args)),
                pool_free=SegmentedPrediction(ModelSegments(), args.models / POOL_FREE_FOLDER),
                pace=self._pace(con, args),
                win_predictor=SegmentedPrediction(ModelSegments(), args.models / WIN_FOLDER),
                win_pool_free=SegmentedPrediction(ModelSegments(), args.models / POOL_FREE_FOLDER / WIN_FOLDER),
                extras=self._extras(attachers, args.timing, SCORE_TOP3_TIMINGS, ABILITY_SCORE_TOP3_TIMINGS, TRACK_BIAS_TOP3_TIMINGS,
                                    WEIGHT_DISCOUNT_TOP3_TIMINGS),
                win_extras=self._extras(attachers, args.timing, SCORE_WIN_TIMINGS, ABILITY_SCORE_WIN_TIMINGS, TRACK_BIAS_WIN_TIMINGS,
                                        WEIGHT_DISCOUNT_WIN_TIMINGS),
            )
            prediction = workflow.run(race_id, args.timing, self._given_odds(args))
        return [PredictionTable(prediction, args.timing, PROBABILITY, self._extra_columns(prediction)).table()]

    def _dataset_builder(self, con: duckdb.DuckDBPyConnection, args: argparse.Namespace) -> DatasetBuilder:
        """その時点のモデルの材料の組み立て。木曜・前日は馬の力の材料、当日は今の材料と券種の支持と馬の力の材料。"""
        if args.timing in ABILITY_TIMINGS:
            return ability_dataset_builder(con, args.figure_cache)
        return race_day_dataset_builder(con, args.figure_cache)

    def _pace(self, con: duckdb.DuckDBPyConnection, args: argparse.Namespace) -> PaceSource | None:
        """展開の予想の結果（P）を足して学んだ時点（木曜）なら、保存した展開のモデルでそのレースを予測する関数。ほかの時点は None。"""
        if args.timing not in PACE_TIMINGS:
            return None
        workflow = DevelopmentPaceWorkflow(args.development_root / "models")
        return lambda race_id, timing, given: workflow.run(con, race_id, timing, given)

    def _extras(self, attachers: MaterialAttachers, timing: PredictionTiming, score_timings: tuple[PredictionTiming, ...],
                ability_score_timings: tuple[PredictionTiming, ...], track_bias_timings: tuple[PredictionTiming, ...],
                weight_discount_timings: tuple[PredictionTiming, ...]) -> list[DataAttachment]:
        """そのモデルの予測用データに足す材料の関数（``MaterialAttachers``）。展開スコア（S）を足して学んだ時点（``score_timings``。3着以内は前日）なら S、
        能力スコア（T）を足して学んだ時点（``ability_score_timings``）なら T、トラックバイアスの補正（U）を足して学んだ時点（``track_bias_timings``）なら U、
        馬体重の表の割引（V）を足して学んだ時点（``weight_discount_timings``）なら V を足す。ほかの時点は無し。"""
        extras: list[DataAttachment] = []
        if timing in score_timings:
            extras.append(attachers.score())
        if timing in ability_score_timings:
            extras.append(attachers.ability_score())
        if timing in track_bias_timings:
            extras.append(attachers.bias())
        if timing in weight_discount_timings:
            extras.append(attachers.weight_discount())
        return extras

    def _given_odds(self, args: argparse.Namespace) -> OddsInput | None:
        """``--odds`` で渡されたオッズ。渡されなければ None。"""
        if not args.odds:
            return None
        return OddsInput.of(args.odds)

    def _extra_columns(self, prediction: pd.DataFrame) -> list[str]:
        """馬名のあとに出す列。前日・当日は単勝オッズ・オッズから見た3着以内率・複勝的中の確率・複勝の期待値
        （見込みの倍率を保存してあれば）・1着になる確率・単勝の期待値を出し、木曜（オッズを使わない）は1着になる確率だけ。
        1着になる確率と単勝の期待値は、1着のモデルがあるときだけ（設計書 15 の 14）。"""
        shown = (WIN_ODDS, TOP3_RATE, PLACE_PROBABILITY, PLACE_VALUE, WIN_PROBABILITY, WIN_VALUE)
        return [column for column in shown if column in prediction.columns]

    def _place_price(self, args: argparse.Namespace) -> PlacePriceEstimator | None:
        """学習のときに保存した複勝の見込みの倍率。無ければ（前の版で学習したモデル）None で、期待値は出さない。"""
        state = PlacePriceRepository(args.models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
