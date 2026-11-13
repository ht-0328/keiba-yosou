"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .fit_payout_command import FitPayoutCommand
from .predict_command import PredictCommand

#: --help に出す使い方。
USAGE = """近走と適性からWIN5の買い目を決める。

配当の見積もりの式を作る（過去の WIN5 の当たり組から。reports/近走と適性からWIN5の買い目を決める/payout_estimator.json に保存する）:

    uv run python -m yosou.form_aptitude_win5_tickets fit-payout
    uv run python -m yosou.form_aptitude_win5_tickets fit-payout --before 2019-01-01

WIN5 の日を予測する（今のモデルの1着の確率から、段階の予算の買い目と、買う（多く・少なく）か見送りかを出す）:

    uv run python -m yosou.form_aptitude_win5_tickets predict
    uv run python -m yosou.form_aptitude_win5_tickets predict --date 2026-11-08 --judge-budget 50 --min-value 1.25 --small-budget 30 --large-budget 100 --favorite-product-line 0.0025

予測の前に、jvdata-store で出馬表など（jvstore sync）と、その日の速報（jvstore realtime --date <開催日>。
締め切り前のオッズ・馬体重・その日の WIN5 の対象レースとキャリーオーバー）を取り込んでおく。
1レース目の締め切り前に1回だけ出す。対象レースごとに、馬体重が出ていれば今のモデルの当日、まだなら前日の1着の確率を使う
（障害はオッズから見た勝率）。1レース 1〜2分かかる。結果は reports/近走と適性からWIN5の買い目を決める/記録/<開催日>.json にも残る。
買うかどうかは判断用の買い目（既定 50点）の日の期待値が線（既定 1.25）以上かで決め、買う日は本命の確率の積（5レースの本命のそろえた
1着の確率のかけ算）が線（既定 0.0025）以上なら多く買う日（既定 100点・1万円）、未満なら少なく買う日（既定 30点・3,000円）の買い目を出す。
見送りの日も少なく買う日の予算の買い目を参考に出す。既定は src/yosou/form_aptitude_win5_tickets/formation/buying_defaults.py。
設計書は docs/design/近走と適性からWIN5の買い目を決める/。
"""


class CommandLine:
    """引数を読み、サブコマンド（fit-payout・predict）を実行し、結果の表を出す。元DB は各コマンドが要る段だけ読むだけで開く。

    ``commands`` を渡すと、そのサブコマンドを使う（テストが、学習済みモデルの代わりを持った ``PredictCommand`` を渡す）。
    """

    def __init__(self, commands: Sequence[FitPayoutCommand | PredictCommand] | None = None) -> None:
        self._commands = tuple(commands) if commands is not None else (FitPayoutCommand(), PredictCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.form_aptitude_win5_tickets", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{fit-payout,predict}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        cli.emit(args.handler(args), args)
