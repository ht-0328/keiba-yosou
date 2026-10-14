"""predict: 登録馬を予測する。"""

from __future__ import annotations

import argparse
from datetime import date

import duckdb

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments, FigureCacheArgument
from yosou.shared.dataset import HORSE_ID

from ..repository import RegistrationEntryInfoRepository, RegistrationListRepository, RegistrationRaceRepository
from ..workflow import REGISTRATION_TIMING, registration_prediction_workflow
from .registration_prediction_table import RegistrationPredictionTable
from ..yosou_name import YOSOU_NAME


class PredictCommand:
    """``predict``: 1レースの登録馬の全員について「出走すれば 3着以内に入る確率」と「出走すれば 1着になる確率」を出す。

    rid か ``--date --venue --race`` でレースを指定する（rid は特別登録から引く。出走馬名表が無くてもよい）。``--date`` と ``--all`` で、
    その日の特別登録のある平地の全レースを順に出す。特別登録が元DB に無ければ、取り込み方を案内して止まる。
    時点は特別登録の1つなので ``--timing`` は無く、オッズも使わないので ``--odds`` も無い（設計書 04 の「コマンドの引数」）。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "predict", help="1レースの登録馬の全員の「出走すれば3着以内に入る確率」と「出走すれば1着になる確率」を出す", allow_abbrev=False,
        )
        parser.add_argument("rid", nargs="?", help="レースの rid（16桁。特別登録から引く）")
        parser.add_argument("--date", type=date.fromisoformat, help="開催日 YYYY-MM-DD（rid を省くとき）")
        parser.add_argument("--venue", help="競馬場の名前かコード（rid を省くとき）")
        parser.add_argument("--race", type=int, help="レース番号（rid を省くとき）")
        parser.add_argument("--all", action="store_true", help="--date の日の、特別登録のある平地の全レースを出す")
        FigureCacheArgument().add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        with db.open_db(args.db) as con:
            race_ids = self._race_ids(args, con)
            workflow = registration_prediction_workflow(con, args.models, args.figure_cache)
            info = RegistrationEntryInfoRepository(con)
            tables: list[Table] = []
            for race_id in race_ids:
                prediction = workflow.run(race_id, REGISTRATION_TIMING)
                merged = prediction.assign(**{HORSE_ID: prediction[HORSE_ID].astype(str)}).merge(info.read(race_id), on=HORSE_ID, how="left")
                tables.append(RegistrationPredictionTable(merged).table())
        return tables

    def _race_ids(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> list[str]:
        """rid か、開催日・競馬場・レース番号か、``--all`` の日の全レース。"""
        if args.rid:
            return [args.rid]
        if args.all:
            return self._all_race_ids(args, con)
        if not (args.date and args.venue and args.race):
            raise ValueError("rid か、--date --venue --race の3つ（または --date と --all）を指定してください")
        return [RegistrationRaceRepository(con).resolve(args.date.isoformat(), args.venue, args.race)]

    def _all_race_ids(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> list[str]:
        """``--all``: ``--date`` の日の、特別登録のある平地の全レース。"""
        if args.date is None:
            raise ValueError("--all には --date（開催日）を指定してください")
        races = RegistrationListRepository(con).read(args.date, args.date)
        if races.empty:
            raise LookupError(f"{args.date} に特別登録のある平地のレースがありません")
        return [str(race_id) for race_id in races["race_id"]]
