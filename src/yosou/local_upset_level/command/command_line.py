"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .predict_command import PredictCommand
from .train_command import TrainCommand

#: --help に出す使い方。
USAGE = """地方のレースの荒れ具合を4段階（固い・中荒れ・大荒れ・超荒れ）で予想する。

荒れ具合は券種（単勝・馬連・3連複・3連単）ごとに、払戻の額で決める（単勝 300/1,500/5,000円、馬連 1,000/6,000/3万円、
3連複 2,000/1.5万/10万円、3連単 1万/10万/100万円 が、中荒れ・大荒れ・超荒れの境。3連単の万馬券が中荒れ、10万馬券が大荒れ）。

学習（券種ごと・3つの時点ごとに LightGBM と CatBoost を学習し、reports/地方のレースの荒れ具合を4段階で予想/models/<券種>/<時点>/ に保存する）:

    uv run python -m yosou.local_upset_level train
    uv run python -m yosou.local_upset_level train --bet 3連複 --config my_settings.toml
    uv run python -m yosou.local_upset_level train --rebuild        # とっておいた学習データを作り直す（新しい成績がたまったとき。30〜60分）

予測（1レースの、券種ごとの荒れ具合の確率。時点は 出馬表・前日・当日の3つ）:

    uv run python -m yosou.local_upset_level predict 2026110544010111 --timing 当日
    uv run python -m yosou.local_upset_level predict --date 2026-11-05 --venue 大井 --race 11 --timing 当日 --bet 3連複
    uv run python -m yosou.local_upset_level predict 2026110544010111 --timing 当日 --odds 1:3.4 2:6.8 3:7.5 …（全頭ぶん）

学習データは1回作って reports/地方のレースの荒れ具合を4段階で予想/cache/ にとっておき、2回目からは読むだけ（--rebuild で作り直す）。
前日・当日は全頭の単勝オッズを使う。--odds で全頭ぶん渡すか、nvstore realtime で締め切り前のオッズを取り込んでおく
（終わったレースは確定オッズを使う。出馬表はオッズを使わず、レースの条件・出走馬の実績のばらつき・過去の荒れ率だけで出す）。
当日は、当日の馬場傾向のレースの値（その日に先に終わった同じ競馬場のレースの傾き。速報 0B15 で当日の成績を取り込んでおく）も使う。
予測の前に、nvdata-store で出馬表（RACE）・出走別着度数地方（SNAP）・マスタ（DIFN）を取り込んでおく（前日と当日は速報も）。
中荒れ以上の確率は、発走前の通知の推奨買目（3連複は 3連複の中荒れ以上の確率 0.6 以上のレースだけ買う）が使う。
設計書は docs/design/地方のレースの荒れ具合を4段階で予想/。
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
            prog="python -m yosou.local_upset_level", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。train は学習データを読み終えたら閉じ、学習のあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
