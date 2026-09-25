"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .evaluate_command import EvaluateCommand
from .predict_command import PredictCommand
from .train_command import TrainCommand

#: --help に出す使い方。
USAGE = """1番人気を「消す」「単勝と複勝を買う」「複勝だけ買う」に分ける。

1番人気だけで、芝ダート × 距離の単位ごとに、勝利・馬券内・馬券外の3つのモデルを、それぞれのグループの馬だけで作る。
対象の1番人気が各モデルにどれだけ近いか（0〜100 の点数）を比べ、馬券外に近ければ消す。
消さなかった馬は、勝利に近ければ単勝と複勝、そうでなければ複勝だけ。

方針（単位のまとめ方・特徴量の時点・k・判定の線・掛け金・評価の年）は setting/default_settings.toml。
変えるときは、変えたい項目だけを書いた TOML を --config で渡して、train か evaluate を実行し直す。

1年ごとの評価（評価の年ごとに、その前年までで学習し直す）:

    uv run python -m yosou.favorite_buy_or_fade evaluate --out reports/favorite_buy_or_fade/evaluation.md
    uv run python -m yosou.favorite_buy_or_fade evaluate --config my_settings.toml

本番用の学習（reports/favorite_buy_or_fade/models/ に保存する）と、1レースの判定:

    uv run python -m yosou.favorite_buy_or_fade train
    uv run python -m yosou.favorite_buy_or_fade predict --date 2026-09-27 --venue 中山 --race 11 --odds 3:2.4 7:5.1 ...

設計書は docs/design/1番人気を買うか消すかを予想/。
"""


class CommandLine:
    """引数を読み、サブコマンド（train・evaluate・predict）を実行し、結果の表を出す。"""

    def __init__(self) -> None:
        self._commands = (TrainCommand(), EvaluateCommand(), PredictCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.favorite_buy_or_fade", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,evaluate,predict}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        cli.emit(args.handler(args), args)
