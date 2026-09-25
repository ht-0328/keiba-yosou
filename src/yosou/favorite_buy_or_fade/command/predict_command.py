"""predict: 1レースの1番人気を判定する。"""

from __future__ import annotations

import argparse

import duckdb

from 共通 import db, race
from 共通.render import Table

from yosou.shared.command import CommonArguments
from yosou.shared.dataset import HORSE_NAME, HORSE_NO, OddsInput, OddsResolver, PopularityApplier, PopularityInput
from yosou.shared.repository import AnnouncedOddsRepository

from ..dataset import dataset_builder
from ..decision import DECISION
from ..repository import SimilarityModelRepository
from ..similarity import SCORE_COLUMNS, UNIT
from ..workflow import PredictionWorkflow
from .yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レースの1番人気について、3つのグループへの近さの点数と判定（消す・単勝と複勝・複勝だけ）を出す。

    特徴量の時点と判定の線は、train のときの方針を使う（変えるときは、設定ファイルを直して train し直す）。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "predict", help="1レースの1番人気の近さの点数と判定を出す", allow_abbrev=False,
        )
        parser.add_argument("rid", nargs="?", help="レースの rid（16桁）")
        parser.add_argument("--date", help="開催日 YYYY-MM-DD（rid を省くとき）")
        parser.add_argument("--venue", help="競馬場の名前かコード（rid を省くとき）")
        parser.add_argument("--race", type=int, help="レース番号（rid を省くとき）")
        parser.add_argument(
            "--pops", nargs="*", default=None, metavar="馬番:人気",
            help="利用者が見た単勝人気（例: --pops 3:1）。省略すると、締め切り前のオッズか、元DB の確定単勝人気を使う",
        )
        parser.add_argument(
            "--odds", nargs="*", default=None, metavar="馬番:オッズ",
            help="利用者が見た単勝オッズを全頭ぶん（例: --odds 3:2.4 7:5.1 …）。--pops を省くと、このオッズの小さい順を人気にする",
        )
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        models = SimilarityModelRepository(args.models).load()
        with db.open_db(args.db) as con:
            race_id = self._race_id(args, con)
            odds_repository = AnnouncedOddsRepository(con)
            workflow = PredictionWorkflow(dataset_builder(con), models, PopularityApplier(odds_repository),
                                          OddsResolver(odds_repository))
            judged = workflow.run(race_id, self._given_popularity(args), self._given_odds(args))
        columns = [HORSE_NO, HORSE_NAME, UNIT, *SCORE_COLUMNS.values(), DECISION]
        rows = judged[columns].astype(object).where(judged[columns].notna(), None).values.tolist()
        return [Table(columns, rows, title=f"1番人気の判定（{race_id}）",
                      note=f"特徴量の時点は{models.settings.timing.label}。点数は 0〜100 で、大きいほどそのグループに近い。")]

    def _given_popularity(self, args: argparse.Namespace) -> PopularityInput | None:
        return PopularityInput.of(args.pops) if args.pops else None

    def _given_odds(self, args: argparse.Namespace) -> OddsInput | None:
        return OddsInput.of(args.odds) if args.odds else None

    def _race_id(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> str:
        """rid か、開催日・競馬場・レース番号から、レースの rid を決める（ほかの道具と同じ指定のしかた）。"""
        if args.rid:
            return args.rid
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つを指定してください")
        return race.resolve_rid(con, args.date, args.venue, args.race)
