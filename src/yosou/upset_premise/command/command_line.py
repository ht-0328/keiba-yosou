"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from yosou.form_aptitude_top3.command.predict_command import PredictCommand
from yosou.form_aptitude_top3.command.train_command import TrainCommand

from ..dataset import WildRaceRows
from .yosou_name import YOSOU_NAME

#: --help に出す使い方。
USAGE = """荒れる前提で着順を予想する（帯 = 払戻 100万円以上を狙うための予想）。

学習（荒れる前提の 3着以内と1着。木曜・前日・当日。reports/荒れる前提で着順を予想/models/ に保存する）:

    uv run python -m yosou.upset_premise train

予測（1レースの、荒れる前提の 3着以内と1着の確率）:

    uv run python -m yosou.upset_premise predict 2026092706040511 --timing 当日

手本の予想（近走と適性から3着以内を予想）と同じ材料・同じ列・同じ引数で、学ぶ行を荒れたレース（3連単の払戻が 10万円以上）だけにしたもの。
開催日ごとのレース選び（荒れ具合の予想の3連単が 1,000倍以上になる確率が線以上のレース）と買い目は、道具「帯狙い」（tools/帯狙い/obi.py）が出す。
設計書は docs/design/荒れる前提で着順を予想/。
"""


class CommandLine:
    """引数を読み、サブコマンド（train・predict）を実行し、結果の表を出す。"""

    def __init__(self) -> None:
        self._commands = (TrainCommand(YOSOU_NAME, WildRaceRows()), PredictCommand(YOSOU_NAME))

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.upset_premise", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。学習は学習データを読み終えたら閉じ、学習のあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
