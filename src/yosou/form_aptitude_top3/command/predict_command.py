"""predict: 1レースを予測する。"""

from __future__ import annotations

import argparse

import duckdb

from 共通 import race
from 共通.render import Table

from ..dataset import DatasetBuilder
from ..feature import PredictionTiming
from ..ml_model import MEMBER_TYPES
from ..repository import ModelRepository
from ..workflow import PredictionWorkflow
from .common_arguments import CommonArguments
from .prediction_table import PredictionTable


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
        CommonArguments().add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> list[Table]:
        race_id = self._race_id(args, con)
        workflow = PredictionWorkflow(
            DatasetBuilder.for_database(con), ModelRepository(args.models, MEMBER_TYPES),
        )
        prediction = workflow.run(race_id, args.timing)
        return [PredictionTable(prediction, args.timing).table()]

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
