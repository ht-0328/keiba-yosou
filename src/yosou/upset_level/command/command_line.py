"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .predict_command import PredictCommand
from .train_command import TrainCommand

#: --help に出す使い方。
USAGE = """レースの荒れ具合を4段階（固い・中荒れ・大荒れ・超荒れ）で予想する。

荒れ具合は券種（単勝・馬連・3連複・3連単）ごとに、払戻の額で決める（単勝 500/1,000/3,000円、馬連 1,000/3,000/1万円、
3連複 3,000/1万/5万円、3連単 2万/10万/50万円 が、中荒れ・大荒れ・超荒れの境）。

学習（券種ごと・3つの時点ごとに LightGBM と CatBoost を学習し、reports/upset_level/models/<券種>/<時点>/ に保存する）:

    uv run python -m yosou.upset_level train
    uv run python -m yosou.upset_level train --bet 3連単 --config my_settings.toml

予測（1レースの、券種ごとの荒れ具合の確率。時点は 木曜・前日・当日の3つ）:

    uv run python -m yosou.upset_level predict 2026092706040511 --timing 当日 --odds 1:3.4 2:6.8 3:7.5 …（全頭ぶん）
    uv run python -m yosou.upset_level predict 2026092706040511 --timing 当日 --bet 3連単
    uv run python -m yosou.upset_level predict --date 2026-09-27 --venue 中山 --race 11 --timing 木曜

前日・当日は全頭の単勝オッズを使う。--odds で全頭ぶん渡すか、jvstore realtime で締め切り前のオッズを取り込んでおく
（終わったレースは確定オッズを使う。木曜はオッズを使わず、レースの条件・出走馬の実績のばらつき・過去の荒れ率だけで出す）。
予測の前に、jvdata-store で出走馬名表・出馬表・出走別着度数を取り込んでおく（前日と当日は速報も）。
設計書は docs/design/レースの荒れ具合を4段階で予想/。
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
            prog="python -m yosou.upset_level", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。train は学習データを読み終えたら閉じ、学習のあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
