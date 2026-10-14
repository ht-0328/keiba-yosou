"""registrations: 登録馬の確かめ。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments, FigureCacheArgument
from yosou.shared.dataset import DEFAULT_TEST_FIRST_DAY

from ..repository import RegistrationEntryInfoRepository, RegistrationListRepository
from ..workflow import DEFAULT_CHECK_MODELS_DIR, DEFAULT_PREDICTIONS_DIR, RegistrationCheckWorkflow, registration_prediction_workflow
from .registration_check_tables import RegistrationCheckTables
from ..yosou_name import YOSOU_NAME


class RegistrationsCommand:
    """``registrations``: テスト期間の特別登録の登録馬の全員に予測を出し、出走した登録馬だけでの当たり具合（登録馬の中で比べた材料の
    ずれ）を出す（設計書 16 の 7）。出走するかどうかは当てないので、出走しなかった馬の割合は出さない。

    モデルは、確かめる期間を学習に使っていないもの（既定は 2026年の区切りのモデル。学習は 2025年6月まで）を ``--models`` で渡す。
    特別登録は 1年分しか無いので、確かめられるのはテスト期間（既定 2026年1月1日から DB にある最後の日まで）だけ。1レース 5秒ほど。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("registrations", help="登録馬の全員に予測を出し、出走した馬の結果で当たり具合を確かめる", allow_abbrev=False)
        parser.add_argument("--from", dest="begin", type=date.fromisoformat, default=DEFAULT_TEST_FIRST_DAY,
                            help=f"確かめる特別登録の最初の開催日（既定: {DEFAULT_TEST_FIRST_DAY}）")
        parser.add_argument("--to", dest="end", type=date.fromisoformat, default=None, help="最後の開催日（省略すると DB にある最後の日）")
        parser.add_argument(
            "--predictions", type=Path, default=DEFAULT_PREDICTIONS_DIR,
            help=f"登録馬の予測の表を書く場所（既定: {DEFAULT_PREDICTIONS_DIR}。registrations.pkl）",
        )
        FigureCacheArgument().add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run, models=DEFAULT_CHECK_MODELS_DIR)

    def run(self, args: argparse.Namespace) -> list[Table]:
        with db.open_db(args.db) as con:
            workflow = RegistrationCheckWorkflow(
                con, registration_prediction_workflow(con, args.models, args.figure_cache),
                RegistrationListRepository(con), RegistrationEntryInfoRepository(con), args.predictions,
            )
            result = workflow.run(args.begin, args.end)
        return RegistrationCheckTables(result).tables()
