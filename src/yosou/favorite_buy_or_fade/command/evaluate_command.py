"""evaluate: 1年ごとに学習し直して、その年の1番人気の判定を確かめる。"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments

from ..dataset import PICK, FavoritePicks, PreDeadlineFavorites
from ..evaluation import EvaluationPeriods, EvaluationTables, PickComparison, StakePlan
from ..repository import PreDeadlineFavoriteRepository
from ..workflow import YEAR, TrainingDataReader, YearlyEvaluation
from .settings_argument import SettingsArgument
from .yosou_name import YOSOU_NAME

#: ``--favorite-odds`` の選び方。確定オッズ（確定単勝人気）か、締め切り前のオッズか。
_CONFIRMED_ODDS = "確定"
_PRE_DEADLINE_ODDS = "締め切り前"
#: 締め切り前のオッズを、発走の何分前までに発表された断面にするか（既定）。
_DEFAULT_MINUTES = 10


class EvaluateCommand:
    """``evaluate``: 方針の評価の年ごとに、その前年までで学習し直して判定し、年ごと・判定ごと・単位ごとの表を出す。

    表は、方針を決める年と確かめる年に分ける（設定の ``[evaluation]`` の ``tune_last_year``。設計書 16 の 6）。
    ``--favorite-odds 締め切り前`` を渡すと、1番人気を締め切り前のオッズで選んで判定し、確定オッズで選んだときとの
    違いの表も出す（締め切り前のオッズの断面があるレースだけ。設計書 16 の 7）。
    ``--rows-out`` を渡すと、判定した1番人気1頭ずつの表も CSV で書く（JV-Data から作ったものなので ``reports/`` に置く）。
    """

    def __init__(self) -> None:
        self._settings_argument = SettingsArgument()

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "evaluate", help="1年ごとに学習し直して判定し、消し・単勝の当たり具合と回収率を出す", allow_abbrev=False,
        )
        self._settings_argument.add_to(parser)
        parser.add_argument("--favorite-odds", choices=[_CONFIRMED_ODDS, _PRE_DEADLINE_ODDS], default=_CONFIRMED_ODDS,
                            help="1番人気を、確定オッズと締め切り前のオッズのどちらで選ぶか（既定: 確定）")
        parser.add_argument("--minutes", type=int, default=_DEFAULT_MINUTES,
                            help="締め切り前のオッズを、発走の何分前までに発表された断面にするか（既定: 10）")
        parser.add_argument("--rows-out", type=Path, default=None,
                            help="判定した1番人気1頭ずつの表を書く CSV のパス（reports/ の下に置く）")
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        settings = self._settings_argument.settings(args)
        with db.open_db(args.db) as con:
            pre_deadline = self._pre_deadline(args, con)
            data = TrainingDataReader(settings, pre_deadline).read(con)
        picks = FavoritePicks(pre_deadline)
        rows = YearlyEvaluation(settings, picks).run(data)
        if args.rows_out is not None:
            args.rows_out.parent.mkdir(parents=True, exist_ok=True)
            rows.to_csv(args.rows_out, index=False, encoding="utf-8-sig")
        plan = StakePlan.of(settings)
        tables = EvaluationTables(plan, YEAR, EvaluationPeriods(settings.tune_last_year, YEAR))
        return [*tables.tables(rows[rows[PICK] == picks.main]), *PickComparison(plan).tables(rows)]

    def _pre_deadline(self, args: argparse.Namespace, con: duckdb.DuckDBPyConnection) -> PreDeadlineFavorites | None:
        """締め切り前のオッズで選ぶなら、その1番人気の一覧。確定オッズで選ぶなら None。"""
        if args.favorite_odds == _CONFIRMED_ODDS:
            return None
        return PreDeadlineFavorites(PreDeadlineFavoriteRepository(con, args.minutes).read())
