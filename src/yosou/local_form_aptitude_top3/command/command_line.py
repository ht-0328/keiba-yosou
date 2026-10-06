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
USAGE = """地方競馬の近走と適性から3着以内を予想する。

学習（時点ごとに LightGBM と CatBoost を学習し、reports/地方競馬の近走と適性から3着以内を予想/models/ に保存する）:

    uv run python -m yosou.local_form_aptitude_top3 train
    uv run python -m yosou.local_form_aptitude_top3 train --config my_settings.toml

予測（1レースの出走馬ごとの「3着以内に入る確率」と「1着になる確率」。時点は 出馬表・前日・当日）:

    uv run python -m yosou.local_form_aptitude_top3 predict 2026101544010111 --timing 前日
    uv run python -m yosou.local_form_aptitude_top3 predict --date 2026-10-15 --venue 大井 --race 11 --timing 当日
    uv run python -m yosou.local_form_aptitude_top3 predict 2026101544010111 --timing 当日 --odds 3:2.4 7:5.1

テスト期間の確かめ（保存したモデルでテスト期間の全レースを予測し直し、市場の確率と比べ、道具「印の成績」が読む予測の表を書く）:

    uv run python -m yosou.local_form_aptitude_top3 backtest

元DB は nvdata-store の nvdata.duckdb（../nvdata-store/nvdata.duckdb か環境変数 YOSOU_LOCAL_DB）。
予測の前に、nvdata-store で出馬表（RACE）・出走別着度数地方（SNAP）・マスタ（DIFN）を取り込んでおく（前日と当日は速報も）。
前日と当日は単勝オッズも使う。--odds で渡すか、nvstore realtime で締め切り前のオッズを取り込んでおく
（終わったレースは確定オッズを使う。出馬表の時点はオッズを使わない）。
当日は、nvstore realtime で全券種の速報オッズ（0B30）も取り込んでおく。無ければ、券種の支持を使わないモデルで予測する。
設計書は docs/design/地方競馬の近走と適性から3着以内を予想/。
"""


class CommandLine:
    """引数を読み、サブコマンド（train・predict・backtest）を実行し、結果の表を出す。元DB は各コマンドが要る段だけ読むだけで開く。"""

    def __init__(self) -> None:
        self._commands = (TrainCommand(), PredictCommand(), BacktestCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.local_form_aptitude_top3", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict,backtest}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。train と backtest は学習データを読み終えたら閉じ、学習・予測のあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
