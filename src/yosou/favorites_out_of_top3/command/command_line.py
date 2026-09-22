"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .predict_command import PredictCommand
from .train_command import TrainCommand

#: --help に出す使い方。
USAGE = """人気馬が4着以下になるかを予想する。

人気馬は、13頭以下のレースなら 1〜3番人気、14頭以上なら 1〜5番人気の馬。

学習（2つの時点ごとに LightGBM と CatBoost を学習し、reports/favorites_out_of_top3/models/ に保存する）:

    uv run python -m yosou.favorites_out_of_top3 train
    uv run python -m yosou.favorites_out_of_top3 train --config my_settings.toml

予測（1レースの人気馬ごとの「4着以下になる確率」。時点は 前日・当日の2つ）:

    uv run python -m yosou.favorites_out_of_top3 predict 2026092706040511 --timing 前日 --pops 3:1 7:2 11:3
    uv run python -m yosou.favorites_out_of_top3 predict --date 2026-09-27 --venue 中山 --race 11 --timing 当日 --pops 3:1,7:2

人気はレースの前に確定しないので、--pops 馬番:人気 で渡す。省略したときは、元DB の締め切り前のオッズか、
終わったレースの確定単勝人気を使う。どちらも無ければ、--pops を渡すよう案内して止まる。

予測の前に、jvdata-store で出馬表・出走別着度数・調教を取り込んでおく（前日と当日は速報も）。
設計書は docs/design/人気馬が4着以下になるかを予想/。
"""


class CommandLine:
    """引数を読み、サブコマンド（train・predict）を実行し、結果の表を出す。元DB は各コマンドが要る段だけ読むだけで開く。"""

    def __init__(self) -> None:
        self._commands = (TrainCommand(), PredictCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.favorites_out_of_top3", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。train は学習データを読み終えたら閉じ、学習のあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
