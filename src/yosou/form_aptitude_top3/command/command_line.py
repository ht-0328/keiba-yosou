"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .predict_command import PredictCommand
from .train_command import TrainCommand

#: --help に出す使い方。
USAGE = """近走と適性から3着以内を予想する。

学習（3つの時点ごとに LightGBM と CatBoost を学習し、reports/form_aptitude_top3/models/ に保存する）:

    uv run python -m yosou.form_aptitude_top3 train
    uv run python -m yosou.form_aptitude_top3 train --config my_settings.toml

予測（1レースの出走馬ごとの「3着以内に入る確率」。時点は 木曜・前日・当日）:

    uv run python -m yosou.form_aptitude_top3 predict 2026092706040511 --timing 前日
    uv run python -m yosou.form_aptitude_top3 predict --date 2026-09-27 --venue 中山 --race 11 --timing 当日

予測の前に、jvdata-store で出走馬名表・出馬表・出走別着度数・調教を取り込んでおく（前日と当日は速報も）。
設計書は docs/design/近走と適性から3着以内を予想/。
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
            prog="python -m yosou.form_aptitude_top3", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。train は学習データを読み終えたら閉じ、学習のあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
