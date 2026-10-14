"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .backtest_command import BacktestCommand
from .predict_command import PredictCommand
from .registrations_command import RegistrationsCommand
from .train_command import TrainCommand

#: --help に出す使い方。
USAGE = """特別登録馬の近走と適性から3着以内を予想する（特別登録の時点。月曜・発走の5〜6日前）。

学習（特別登録の時点の 3着以内と1着のモデルを LightGBM と CatBoost で学習し、reports/特別登録馬の近走と適性から3着以内を予想/models/ に保存する）:

    uv run python -m yosou.special_registration_top3 train
    uv run python -m yosou.special_registration_top3 train --config my_settings.toml

予測（1レースの登録馬の全員の「出走すれば 3着以内に入る確率」と「出走すれば 1着になる確率」。時点は特別登録の1つ）:

    uv run python -m yosou.special_registration_top3 predict 2026101806050411
    uv run python -m yosou.special_registration_top3 predict --date 2026-10-18 --venue 東京 --race 11
    uv run python -m yosou.special_registration_top3 predict --date 2026-10-18 --all

7つの区切りでの確かめ（中央と同じ7つの半年の区切りで学習し直し、テスト期間の特別競走の行で当たり具合を測り、道具「印の成績」が読む予測の表を書く。2〜3時間）:

    uv run python -m yosou.special_registration_top3 backtest
    uv run python -m yosou.special_registration_top3 backtest --variant 相手と比べない
    uv run python -m yosou.special_registration_top3 backtest --compare reports/既存モデルの改善/predictions/ascore_thursday/ascore-thursday.pkl

登録馬の確かめ（テスト期間の特別登録の登録馬の全員に予測を出し、出走した馬の結果で当たり具合を確かめる）:

    uv run python -m yosou.special_registration_top3 registrations

元DB は jvdata-store の jvdata.duckdb（../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）。
予測の前に、jvdata-store で特別登録（TOKU。今週・来週分は sync、過去分は fetch --dataspec TOKU --option 1）と、
確定成績・調教・マスタ（sync）を取り込んでおく。出走馬名表・オッズ・速報は要らない（あっても読まない）。
設計書は docs/design/特別登録馬の近走と適性から3着以内を予想/。
"""


class CommandLine:
    """引数を読み、サブコマンド（train・predict・backtest・registrations）を実行し、結果の表を出す。元DB は各コマンドが要る段だけ読むだけで開く。"""

    def __init__(self) -> None:
        self._commands = (TrainCommand(), PredictCommand(), BacktestCommand(), RegistrationsCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.special_registration_top3", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict,backtest,registrations}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。train と backtest は学習データを読み終えたら閉じ、学習・予測のあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
