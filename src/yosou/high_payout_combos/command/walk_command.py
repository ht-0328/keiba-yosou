"""walk: 年ごとに学んで次の年を予測し、買い目の成績を出す（確かめ用）。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通.render import Table

from yosou.shared.betting import TicketType
from yosou.shared.command import CommonArguments
from yosou.shared.setting import HyperparameterSettings

from ..betting import HighPayoutRule
from ..dataset import DEFAULT_BANDS, DEFAULT_VALUE_LINE
from ..dataset.column_names import RACE_DATE
from ..evaluation import YearlyPickSummary
from ..evaluation.yearly_pick_summary import COLUMNS as SUMMARY_COLUMNS
from ..repository import ComboTableRepository, PredictionStore
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import WalkForwardWorkflow, WalkYearResult
from .folder_arguments import add_folder_argument
from .progress import print_progress
from .ticket_argument import add_ticket_argument, ticket_types_of
from .yosou_name import YOSOU_NAME

#: 予測を始める年の既定。
DEFAULT_FIRST_YEAR = 2020
_PREDICTED, _SKIPPED = "予測した", "済んでいるので飛ばした"
#: 木の数を並べるモデルの名前（共有のモデルのクラスの ``name``）。
_MEMBER_NAMES = ("LightGBM", "CatBoost")


class WalkCommand:
    """``walk``: テストの年ごとに、2年前までで学び、1年前で早期終了し、その年の対象の組を全部予測して保存する。
    予測から、買い目の決まり（高配当の線以上・上限未満で、期待値が線以上の組を全部 100円ずつ）の年ごとの成績を出す。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("walk", help="年ごとに学んで次の年を予測し、買い目の年ごとの成績を出す（確かめ用）", allow_abbrev=False)
        parser.add_argument("--first-year", type=int, default=DEFAULT_FIRST_YEAR, help=f"予測を始める年（既定: {DEFAULT_FIRST_YEAR}）")
        parser.add_argument(
            "--value-line", type=float, default=DEFAULT_VALUE_LINE,
            help=f"成績を数えるときの期待値の線（既定: {DEFAULT_VALUE_LINE}。予測そのものは変わらない）",
        )
        parser.add_argument("--config", type=Path, default=None, help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）")
        parser.add_argument("--force", action="store_true", help="前に作った予測のある年も学び直す（省略すると飛ばして、続きの年から再開する）")
        add_ticket_argument(parser)
        add_folder_argument(parser, "tables")
        add_folder_argument(parser, "predictions")
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB は使わない（保存した組の表から学ぶ）。"""
        settings = HyperparameterSettings.load(args.config, defaults=DEFAULT_SETTINGS_PATH)
        store = PredictionStore(args.predictions)
        workflow = WalkForwardWorkflow(
            ComboTableRepository(args.tables), store, settings, overwrite=args.force, progress=print_progress,
        )
        summary = YearlyPickSummary(HighPayoutRule(DEFAULT_BANDS, args.value_line))
        tables: list[Table] = []
        for ticket_type in ticket_types_of(args):
            results = workflow.run(ticket_type, args.first_year)
            tables += [self._training_table(ticket_type, results), self._summary_table(ticket_type, results, store, summary, args.value_line)]
        return tables

    def _training_table(self, ticket_type: TicketType, results: list[WalkYearResult]) -> Table:
        rows = [self._training_row(result) for result in results]
        columns = ["テストの年", "学習の行", "検証の行", "木の数（LightGBM）", "木の数（CatBoost）", "予測した組", "状態"]
        return Table(columns, rows, title=f"{ticket_type.label}: 年ごとの学習", note="学習と検証の行の数は、外れの組を間引いた後。")

    def _training_row(self, result: WalkYearResult) -> list[object]:
        if result.was_skipped:
            return [result.year, None, None, None, None, None, _SKIPPED]
        tree_counts = [result.tree_counts.get(name) for name in _MEMBER_NAMES]
        return [result.year, result.train_row_count, result.valid_row_count, *tree_counts, result.predicted_row_count, _PREDICTED]

    def _summary_table(self, ticket_type: TicketType, results: list[WalkYearResult], store: PredictionStore,
                       summary: YearlyPickSummary, value_line: float) -> Table:
        """この回に予測した年の、買い目の成績。"""
        predictions = store.load(ticket_type)
        years = [result.year for result in results]
        this_run = predictions[predictions[RACE_DATE].dt.year.isin(years)]
        band = DEFAULT_BANDS[ticket_type]
        note = f"オッズ {band.high_line:g}倍以上・{band.cap:g}倍未満で、期待値（2つのモデルの平均の確率 × オッズ）が {value_line:g} 以上の組を全部 100円ずつ。"
        return Table(list(SUMMARY_COLUMNS), summary.summarize(this_run).to_numpy().tolist(), title=f"{ticket_type.label}: 買い目の年ごとの成績", note=note)
