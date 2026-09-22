"""predict: 1レースの穴馬を予測する。"""

from __future__ import annotations

import argparse

import duckdb

from 共通 import db, race
from 共通.render import Table

from yosou.shared.command import CommonArguments, PredictionTable
from yosou.shared.dataset import PopularityApplier, PopularityInput
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.group import POPULARITY_RANK
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import AnnouncedOddsRepository, ModelRepository

from ..dataset import LONGSHOT_ZONE, ZONE_CHOICES, LongshotZone, LongshotZoneFilter, dataset_builder
from ..workflow import PROBABILITY, TIMING_CHOICES, PredictionWorkflow
from .yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レースの穴馬ごとの「3着以内に入る確率」を出す。``--zone`` で中穴か大穴に絞れる。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "predict", help="1レースの穴馬ごとの「3着以内に入る確率」を出す", allow_abbrev=False,
        )
        parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
        parser.add_argument("--date", help="開催日 YYYY-MM-DD（rid を省くとき）")
        parser.add_argument("--venue", help="競馬場の名前かコード（rid を省くとき）")
        parser.add_argument("--race", type=int, help="レース番号（rid を省くとき）")
        parser.add_argument(
            "--timing", type=PredictionTiming.parse, required=True,
            help=f"予測する時点: {TIMING_CHOICES}",
        )
        parser.add_argument(
            "--pops", nargs="*", default=None, metavar="馬番:人気",
            help="利用者が見た単勝人気を全頭ぶん（例: --pops 3:1 7:2 … や --pops 3:1,7:2,…）。"
                 "木曜は馬番が無いので 馬名:人気 で渡す。前日・当日で省略すると、締め切り前のオッズか、"
                 "元DB の単勝人気（終わったレースの確定単勝人気）を使う",
        )
        parser.add_argument(
            "--zone", choices=[zone.label for zone in LongshotZone], default=None,
            help=f"出す穴馬を絞る区分: {ZONE_CHOICES}（省略すると穴馬すべて）",
        )
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        with db.open_db(args.db) as con:
            race_id = self._race_id(args, con)
            workflow = PredictionWorkflow(
                dataset_builder(con), ModelRepository(args.models, MEMBER_TYPES),
                PopularityApplier(AnnouncedOddsRepository(con)), LongshotZoneFilter(),
            )
            prediction = workflow.run(race_id, args.timing, self._given_popularity(args), self._zone(args))
        table = PredictionTable(prediction, args.timing, PROBABILITY, [POPULARITY_RANK, LONGSHOT_ZONE])
        return [table.table()]

    def _given_popularity(self, args: argparse.Namespace) -> PopularityInput | None:
        """``--pops`` で渡された人気。渡されなければ None。"""
        if not args.pops:
            return None
        return PopularityInput.of(args.pops)

    def _zone(self, args: argparse.Namespace) -> LongshotZone | None:
        """``--zone`` で渡された区分。渡されなければ None（穴馬すべて）。"""
        if not args.zone:
            return None
        return LongshotZone.parse(args.zone)

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
