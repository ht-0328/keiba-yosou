"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .tables_command import TablesCommand
from .train_command import TrainCommand
from .walk_command import WalkCommand

#: --help に出す使い方。
USAGE = """高配当の組（ワイド・馬連・馬単・3連複・3連単）が当たる確率を予想する。

材料は、5券種のオッズの板（市場の確率）と、馬ごとの予想（今の本番の予想の確率・印・危険な人気馬）。モデルは、その券種の
オッズから見た組の確率を出発点にして、そこからの上げ下げだけを学ぶ（LightGBM と CatBoost の平均）。
買うのは、オッズが高配当の線以上・上限未満で、期待値（確率 × オッズ）が 1.05 以上の組。

組の表（材料と、当たったか）を作る。月ごとに元DB の確定オッズの板と払戻を読む（3連単は1年で数百万行）:

    uv run python -m yosou.high_payout_combos tables --from 2015-01-01 --to 2026-06-28
    uv run python -m yosou.high_payout_combos tables --ticket ワイド 馬連 --force

年ごとに学んで次の年を予測し、買い目の年ごとの成績を出す（確かめ用。reports/高配当の組が当たるかを予想/predictions/ に保存する）:

    uv run python -m yosou.high_payout_combos walk --first-year 2020
    uv run python -m yosou.high_payout_combos walk --ticket 3連複

本番のモデルを学習する（reports/高配当の組が当たるかを予想/models/<券種の英名>/ に保存する）:

    uv run python -m yosou.high_payout_combos train

馬ごとの表（reports/高配当の組が当たるかを予想/horses/*.parquet。過去のレースの、学習に使っていない期間の予測に本番と同じ印を
付けたもの）は、別の道具が作る。1レースの予測（締め切り前の板から、買う組を出す）も、このパッケージの HighPayoutPredictor と
HighPayoutRule を使う道具の側が行う。
"""


class CommandLine:
    """引数を読み、サブコマンド（tables・walk・train）を実行し、結果の表を出す。元DB は ``tables`` だけが、月ごとに読む間だけ開く。"""

    def __init__(self) -> None:
        self._commands = (TablesCommand(), WalkCommand(), TrainCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.high_payout_combos", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{tables,walk,train}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        cli.emit(args.handler(args), args)
