"""predict: 1レースを予測する。"""

from __future__ import annotations

import argparse

import duckdb
import pandas as pd

from 共通 import db, race
from 共通.render import Table

from yosou.form_aptitude_materials import MaterialAttachers
from yosou.shared.command import CommonArguments, DevelopmentRootArgument, FigureCacheArgument, PredictionTable
from yosou.shared.dataset import OddsInput
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.group import WIN_ODDS
from yosou.shared.feature.odds import TOP3_RATE
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE
from yosou.shared.win_value import WIN_VALUE
from yosou.shared.workflow import PROBABILITY, WIN_PROBABILITY, FormAptitudePrediction

from .yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レースの出走馬ごとの「3着以内に入る確率」と「1着になる確率」（と、前日・当日は複勝・単勝の期待値）を出す。

    予測の流れの組み立ては、道具「今週の予想」と同じ ``FormAptitudePrediction``（``yosou.shared.workflow``）に、
    材料を作る部品 ``MaterialAttachers``（``yosou.form_aptitude_materials``）を渡して行う。
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
        prediction_flow = FormAptitudePrediction(
            args.models, lambda con: MaterialAttachers(con, args.development_root), args.figure_cache,
        )
        with db.open_db(args.db) as con:
            race_id = self._race_id(args, con)
            prediction = prediction_flow.run(con, race_id, args.timing, self._given_odds(args))
        return [PredictionTable(prediction, args.timing, PROBABILITY, self._extra_columns(prediction)).table()]

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

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
