"""backtest: 7つの区切りでの確かめ。"""

from __future__ import annotations

import argparse
from pathlib import Path

from 共通 import db
from 共通.render import Table

from yosou.shared.command import CommonArguments, FigureCacheArgument
from yosou.shared.dataset import TOP3, WIN

from ..dataset import registration_dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import (
    ALL_FEATURES,
    DEFAULT_PREDICTIONS_DIR,
    DEFAULT_WINDOW_MODELS_DIR,
    VARIANTS,
    WINDOWS,
    WindowedBacktestWorkflow,
    windows_named,
)
from .period_arguments import PeriodArguments
from .windowed_backtest_tables import WindowedBacktestTables
from ..yosou_name import YOSOU_NAME


class BacktestCommand:
    """``backtest``: 中央と同じ7つの半年の区切りで学習し直し、テスト期間の特別競走の行で当たり具合を測る（設計書 16 の 4）。

    学習データを全期間で1回作り、区切りごとに ``WindowedBacktestWorkflow`` が学習と確かめを行う。区切りごとのモデルは ``--models-root``
    （既定 ``reports/特別登録馬の近走と適性から3着以内を予想/models-区切り/<区切り>/``）、予測の表（道具「印の成績」が読む形）は ``--predictions`` に書く。
    ``--variant 相手と比べない`` は、相手と比べる材料の 70個を外した版。``--compare`` と ``--compare-win`` に中央の木曜のモデルの7つの区切りの
    予測の表を渡すと、同じレース・同じ馬で比べる。学習を 7回 × 2つの目的変数くり返すので、2〜3時間かかる。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("backtest", help="7つの区切りで学習し直し、テスト期間の特別競走で当たり具合を測る", allow_abbrev=False)
        parser.add_argument(
            "--windows", nargs="+", default=None, metavar="区切り",
            help=f"回す区切り（{' / '.join(window.name for window in WINDOWS)}。省略すると7つ全部）",
        )
        parser.add_argument(
            "--variant", choices=VARIANTS, default=ALL_FEATURES,
            help=f"材料の版（既定: {ALL_FEATURES}。「相手と比べない」は同じレースの相手と比べる材料 70個を外した版）",
        )
        parser.add_argument("--compare", type=Path, default=None, help="中央の木曜のモデルの7つの区切りの予測の表（3着以内。pkl）。渡すと同じレース・同じ馬で比べる")
        parser.add_argument("--compare-win", type=Path, default=None, help="同じく1着の予測の表（pkl）")
        parser.add_argument(
            "--models-root", type=Path, default=DEFAULT_WINDOW_MODELS_DIR,
            help=f"区切りごとのモデルの置き場所（既定: {DEFAULT_WINDOW_MODELS_DIR}）",
        )
        parser.add_argument(
            "--predictions", type=Path, default=DEFAULT_PREDICTIONS_DIR,
            help=f"予測の表を書く場所（既定: {DEFAULT_PREDICTIONS_DIR}。thursday.pkl と thursday-1着.pkl。版を変えると名前に版が付く）",
        )
        PeriodArguments(with_split=False).add_to(parser)
        FigureCacheArgument().add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        """元DB を開くのは学習データを読む段だけ。学習と確かめは DB を閉じてから行う。"""
        windows = windows_named(args.windows)
        period = PeriodArguments().period_of(args)
        compare = {label: path for label, path in ((TOP3, args.compare), (WIN, args.compare_win)) if path is not None}
        with db.open_db(args.db) as con:
            data = registration_dataset_builder(con, args.figure_cache).build_training_data(period)
        workflow = WindowedBacktestWorkflow(
            args.models_root, args.predictions, DEFAULT_SETTINGS_PATH, period.warmup_first_day, period.train_first_day,
            variant=args.variant, compare=compare,
        )
        return WindowedBacktestTables(workflow.run(data, windows)).tables()
