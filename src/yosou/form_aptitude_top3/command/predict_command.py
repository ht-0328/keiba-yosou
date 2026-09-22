"""predict: 1レースを予測する。"""

from __future__ import annotations

import argparse

import duckdb
import pandas as pd

from 共通 import db, race
from 共通.render import Table

from yosou.shared.command import CommonArguments, PredictionTable
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import AnnouncedOddsRepository, ModelRepository

from ..dataset import OddsInput, OddsResolver, dataset_builder
from ..feature import WIN_ODDS
from ..workflow import PROBABILITY, PredictionWorkflow
from .yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レースの出走馬ごとの「3着以内に入る確率」を出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "predict", help="1レースの出走馬ごとの「3着以内に入る確率」を出す", allow_abbrev=False,
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
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        with db.open_db(args.db) as con:
            race_id = self._race_id(args, con)
            workflow = PredictionWorkflow(
                dataset_builder(con), ModelRepository(args.models, MEMBER_TYPES),
                OddsResolver(AnnouncedOddsRepository(con)),
            )
            prediction = workflow.run(race_id, args.timing, self._given_odds(args))
        return [PredictionTable(prediction, args.timing, PROBABILITY, self._extra_columns(prediction)).table()]

    def _given_odds(self, args: argparse.Namespace) -> OddsInput | None:
        """``--odds`` で渡されたオッズ。渡されなければ None。"""
        if not args.odds:
            return None
        return OddsInput.of(args.odds)

    def _extra_columns(self, prediction: pd.DataFrame) -> list[str]:
        """馬名のあとに出す列。前日・当日は単勝オッズを出し、木曜（オッズを使わない）は出さない。"""
        if WIN_ODDS not in prediction.columns:
            return []
        return [WIN_ODDS]

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
