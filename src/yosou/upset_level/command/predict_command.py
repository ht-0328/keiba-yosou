"""predict: 1レースの荒れ具合を予測する。"""

from __future__ import annotations

import argparse

import duckdb

from 共通 import db, race
from 共通.render import Table

from yosou.shared.command import CommonArguments, RacePredictionTable
from yosou.shared.dataset import OddsInput, OddsResolver
from yosou.shared.feature import PredictionTiming
from yosou.shared.repository import AnnouncedOddsRepository

from ..dataset import BET_CHOICES, BetType, race_dataset_builder
from ..workflow import PREDICTION_COLUMNS, TIMING_CHOICES, PredictionWorkflow, model_repositories
from .yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レースの、券種ごとの荒れ具合（固い・中荒れ・大荒れ・超荒れ）の確率を出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "predict", help="1レースの、券種ごとの荒れ具合の確率を出す", allow_abbrev=False,
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
            "--odds", nargs="*", default=None, metavar="馬番:オッズ",
            help="利用者が見た単勝オッズを全頭ぶん（例: --odds 1:3.4 2:6.8 … や --odds 1:3.4,2:6.8,…）。前日と当日に使う。"
                 "省略すると、締め切り前のオッズか、元DB の単勝オッズ（終わったレースの確定オッズ）を使う",
        )
        parser.add_argument(
            "--bet", nargs="*", default=None, choices=[bet.label for bet in BetType], metavar="券種",
            help=f"出す券種: {BET_CHOICES}（省略すると4つ全部）",
        )
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        with db.open_db(args.db) as con:
            race_id = self._race_id(args, con)
            workflow = PredictionWorkflow(
                race_dataset_builder(con), model_repositories(args.models),
                OddsResolver(AnnouncedOddsRepository(con)),
            )
            prediction = workflow.run(race_id, args.timing, self._given_odds(args), self._bets(args))
        table = RacePredictionTable(
            prediction, args.timing, PREDICTION_COLUMNS,
            note="確率は LightGBM と CatBoost の平均。中荒れ以上の確率は、固い以外の3つの合計。",
        )
        return [table.table()]

    def _given_odds(self, args: argparse.Namespace) -> OddsInput | None:
        """``--odds`` で渡されたオッズ。渡されなければ None。"""
        if not args.odds:
            return None
        return OddsInput.of(args.odds)

    def _bets(self, args: argparse.Namespace) -> list[BetType] | None:
        """``--bet`` で渡された券種。渡されなければ None（4つ全部）。"""
        if not args.bet:
            return None
        return [BetType.parse(text) for text in args.bet]

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
