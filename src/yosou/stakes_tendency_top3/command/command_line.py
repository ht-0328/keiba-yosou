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
USAGE = """重賞（G1・G2・G3）の傾向と近走から3着以内を予想する。

【引退】この予想は、7つの区切りで一般の予想（近走と適性から3着以内を予想）に勝てなかったので 2026-10-02 に引退した。
重賞も一般の予想で予想する（uv run python -m yosou.form_aptitude_top3 predict ...）。train・predict・evaluate は確かめ直し用に残す。

対象は重賞だけ。手本（近走と適性から3着以内を予想）と同じ材料（木曜・前日は馬の力の材料、当日は今の材料に
券種ごとの支持と馬の力の材料を足したもの）に、レースごとの傾向（過去の開催から数えた、1番人気の信頼度・
前に行く馬・内枠などのずれ）を足して、重賞だけで学ぶ。
レースごとの傾向そのものを読みたいときは、分析ツール（uv run python tools/重賞攻略/stakes.py --name 有馬）を使う。

学習（3つの時点ごとに LightGBM と CatBoost を学習し、reports/重賞の傾向と近走から3着以内を予想/models/ に保存する）:

    uv run python -m yosou.stakes_tendency_top3 train
    uv run python -m yosou.stakes_tendency_top3 train --config my_settings.toml

予測（1レース（重賞）の出走馬ごとの「3着以内に入る確率」。時点は 木曜・前日・当日）:

    uv run python -m yosou.stakes_tendency_top3 predict --date 2026-09-27 --venue 中山 --race 11 --timing 当日
    uv run python -m yosou.stakes_tendency_top3 predict 2026092706040511 --timing 前日
    uv run python -m yosou.stakes_tendency_top3 predict 2026092706040511 --timing 当日 --odds 3:2.4 7:5.1

評価（学習に使っていない期間の重賞で、複勝の期待値買いの回収率と、本命と1番人気の比べ方を出す）:

    uv run python -m yosou.stakes_tendency_top3 evaluate

予測の前に、jvdata-store で出走馬名表・出馬表・出走別着度数・調教を取り込んでおく（前日と当日は速報も）。
前日と当日は単勝オッズも使う。--odds で渡すか、jvstore realtime で締め切り前のオッズを取り込んでおく
（終わったレースは確定オッズを使う。木曜はオッズを使わない）。
当日は、jvstore realtime で全券種の速報オッズ（0B30）も取り込んでおく。無ければ、券種の支持を使わないモデルで予測する。
設計書は docs/design/重賞の傾向と近走から3着以内を予想/。引退の判断と理由は設計書 15 の 9。
"""


class CommandLine:
    """引数を読み、サブコマンド（train・predict・evaluate）を実行し、結果の表を出す。元DB は各コマンドが要る段だけ読むだけで開く。"""

    def __init__(self) -> None:
        self._commands = (TrainCommand(), PredictCommand(), EvaluateCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.stakes_tendency_top3", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict,evaluate}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。学習・評価は読み終えたら閉じ、そのあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
