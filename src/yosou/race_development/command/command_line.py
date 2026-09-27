"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .backtest_command import BacktestCommand
from .predict_command import PredictCommand
from .train_command import TrainCommand

#: --help に出す使い方。
USAGE = """既存の予想から見たレースの傾向に合う展開（前半と後半）と着順を予想し、過去のレースで券種ごと・年ごとの的中率と回収率を確かめる。

まず既存の4つの予想（近走と適性から3着以内・人気馬が4着以下・穴馬が3着以内・レースの荒れ具合）で、このレースの傾向を出す。
その結果を、前半（① 先頭の馬・② 序盤の位置・③ 前半のペース）の特徴量に入れ、前半の結果を後半（④ 4コーナーの位置・
⑤ 上がりの速さ・⑥ 後半のペース）の特徴量に入れ、前半と後半の結果を着順（⑦ 1着の確率）の特徴量に入れる。
1着の確率から 2着・3着と買い目ごとの確率を出し、印（◎○▲△☆注）と買い目を決める。

学習（時点ごとに、既存の4つの予想と7つの予想のモデルを学習し、reports/race_development/models/ に保存する）:

    uv run python -m yosou.race_development train
    uv run python -m yosou.race_development train --timings 当日

予測（1レースの展開と着順、印と印どおりの買い目。時点は 木曜・前日・当日の3つ）:

    uv run python -m yosou.race_development predict 2026100404050311 --timing 前日

年ごとの確かめ（2021〜2026年の各年を、その前の年までのデータだけで学習し直して、当日の時点で予測する）:

    uv run python -m yosou.race_development backtest
    uv run python -m yosou.race_development backtest --years 2024-2026

途中の結果（学習データ・年ごとの予測・精算の表）は reports/race_development/ に残し、止まったら続きから再開する。
結果の表は reports/race_development/backtest/results.md にも書く。設計書は docs/design/展開から着順を予想/。
"""


class CommandLine:
    """引数を読み、サブコマンドを実行し、結果の表を出す。"""

    def __init__(self) -> None:
        self._commands = (TrainCommand(), PredictCommand(), BacktestCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.race_development", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict,backtest}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        cli.emit(args.handler(args), args)
