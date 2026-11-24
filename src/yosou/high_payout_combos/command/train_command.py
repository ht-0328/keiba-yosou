"""train: 本番のモデルを学習して保存する。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通.render import Table

from yosou.shared.betting import TicketType
from yosou.shared.command import CommonArguments
from yosou.shared.setting import HyperparameterSettings

from ..evaluation import AVERAGE, MARKET, SCALED_MARKET
from ..repository import ComboTableRepository, TicketModelRepository
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import ProductionTraining, ProductionTrainingResult
from .folder_arguments import add_folder_argument
from .progress import print_progress
from .ticket_argument import add_ticket_argument, ticket_types_of
from .yosou_name import YOSOU_NAME

#: 対数損失は小さい数なので、1,000倍して見せる。
_LOSS_SCALE = 1000.0
_LOSS_NAMES = ("LightGBM", "CatBoost", AVERAGE, MARKET, SCALED_MARKET)


class TrainCommand:
    """``train``: 券種ごとに、表のある最後の開催日の1年前までで学び、最後の1年で早期終了して、本番のモデルを保存する。"""

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("train", help="本番のモデル（券種ごとに LightGBM と CatBoost）を学習して保存する", allow_abbrev=False)
        parser.add_argument("--config", type=Path, default=None, help="ハイパーパラメータの設定ファイル（TOML。省略すると初期値）")
        add_ticket_argument(parser)
        add_folder_argument(parser, "tables")
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB は使わない（保存した組の表から学ぶ）。"""
        settings = HyperparameterSettings.load(args.config, defaults=DEFAULT_SETTINGS_PATH)
        training = ProductionTraining(ComboTableRepository(args.tables), TicketModelRepository(args.models), settings)
        results = [self._train(training, ticket_type) for ticket_type in ticket_types_of(args)]
        return [self._period_table(results), self._loss_table(results)]

    def _train(self, training: ProductionTraining, ticket_type: TicketType) -> ProductionTrainingResult:
        result = training.run(ticket_type)
        print_progress(f"{ticket_type.label}: 木の数 {result.tree_counts} → {result.folder}")
        return result

    def _period_table(self, results: list[ProductionTrainingResult]) -> Table:
        rows = [
            [result.ticket_type.label, str(result.train_last_day), str(result.valid_last_day), result.train_row_count,
             result.valid_row_count, *result.tree_counts.values()]
            for result in results
        ]
        columns = ["券種", "学習の最後の開催日", "検証の最後の開催日", "学習の行", "検証の行", "木の数（LightGBM）", "木の数（CatBoost）"]
        return Table(columns, rows, title="学習した本番のモデル", note="行の数は、外れの組を間引いた後。木の数は、検証の行で早期終了して決めた。")

    def _loss_table(self, results: list[ProductionTrainingResult]) -> Table:
        rows = [self._loss_row(result) for result in results]
        note = (
            "検証の行（最後の1年。重みつき）での対数損失 × 1,000。小さいほど当たっている。"
            "「市場との差」は 市場（当たりの数にそろえた）− 平均 で、正ならモデルのほうが当たっている。"
            "検証の行は木の数を決めるのに使っているので目安（未見の年での確かめは walk）。"
        )
        return Table(["券種", *_LOSS_NAMES, "市場との差"], rows, title="検証の期間での当たり具合（市場の確率との比べ）", note=note)

    def _loss_row(self, result: ProductionTrainingResult) -> list[object]:
        losses = [result.losses[name] * _LOSS_SCALE for name in _LOSS_NAMES]
        gain = (result.losses[SCALED_MARKET] - result.losses[AVERAGE]) * _LOSS_SCALE
        return [result.ticket_type.label, *(f"{loss:.4f}" for loss in losses), f"{gain:.4f}"]
