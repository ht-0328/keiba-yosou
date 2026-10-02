"""コマンドの入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import NoReturn

from 共通 import cli

from .calibration_command import CalibrationCommand
from .predict_command import PredictCommand
from .train_command import TrainCommand

#: --help に出す使い方。
USAGE = """穴馬が3着以内に入るかを予想する。

穴馬は、13頭以下のレースなら 4番人気以下、14頭以上なら 6番人気以下の馬（人気馬の裏返し）。

学習（3つの時点ごとに LightGBM と CatBoost を学習し、reports/穴馬が3着以内に入るかを予想/models/ に保存する）:

    uv run python -m yosou.longshots_in_top3 train
    uv run python -m yosou.longshots_in_top3 train --config my_settings.toml

予測（1レースの穴馬ごとの「3着以内に入る確率」。時点は 木曜・前日・当日の3つ）:

    uv run python -m yosou.longshots_in_top3 predict 2026092706040511 --timing 前日 --pops 3:1 7:2 11:3 …（全頭ぶん）
    uv run python -m yosou.longshots_in_top3 predict 2026092706040511 --timing 当日 --zone 中穴
    uv run python -m yosou.longshots_in_top3 predict 2026092706040511 --timing 当日 --min-value 1.2
    uv run python -m yosou.longshots_in_top3 predict --date 2026-09-25 --venue 中山 --race 11 --timing 木曜 --pops 馬名A:1 馬名B:2 …

人気はレースの前に確定しないので、--pops で全頭ぶん渡す（前日・当日は 馬番:人気、馬番がまだ無い木曜は 馬名:人気）。
前日・当日で省略したときは、元DB の締め切り前のオッズか、終わったレースの確定単勝人気を使う。
どれも無ければ、--pops を渡すよう案内して止まる。人気の分からない馬が1頭でもいても止まる。

--zone 中穴 か --zone 大穴 を付けると、その区分の穴馬だけを出す。付けなければ穴馬すべてを出す。
区分は 13頭以下なら 4〜6番人気が中穴・7番人気以下が大穴、14頭以上なら 6〜9番人気が中穴・10番人気以下が大穴。

前日・当日は、複勝の期待値が「買い」の線以上の穴馬に「買い」を付ける。線は train のときに検証期間で決めた
時点 × 区分ごとの値（models/buy_lines.json）。--min-value を付けると、その値に置き換える。
前日・当日は複勝オッズも使うので、元DB に無ければ jvstore realtime で取り込むよう案内して止まる。

確率のずれの確認（保存したモデルの「3着以内に入る確率」と実際の割合、複勝の期待値と実際の回収率、
「買い」の線で買ったときの成績を、学習に使っていない検証・テストの期間で、時点 × 中穴・大穴ごとに比べる。
学習のときと同じ期間の区切りを渡す）:

    uv run python -m yosou.longshots_in_top3 calibration --out reports/穴馬が3着以内に入るかを予想/calibration.md

予測の前に、jvdata-store で出走馬名表・出馬表・出走別着度数・調教を取り込んでおく（前日と当日は速報とオッズも）。
設計書は docs/design/穴馬が3着以内に入るかを予想/。
"""


class CommandLine:
    """引数を読み、サブコマンド（train・predict・calibration）を実行し、結果の表を出す。元DB は各コマンドが要る段だけ読むだけで開く。"""

    def __init__(self) -> None:
        self._commands = (TrainCommand(), PredictCommand(), CalibrationCommand())

    def run(self, argv: Sequence[str] | None = None) -> NoReturn:
        """``argv`` を省略すると、コマンドラインの引数を読む。誤りは1行で見せて exit 1、成功なら exit 0。"""
        cli.run(self._parser(), self._execute, argv)

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="python -m yosou.longshots_in_top3", description=USAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False,
        )
        subparsers = parser.add_subparsers(dest="command", required=True, metavar="{train,predict,calibration}")
        for command in self._commands:
            command.add_parser(subparsers)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        """元DB を開くのは各コマンド。train は学習データを読み終えたら閉じ、学習のあいだロックを持たない。"""
        cli.emit(args.handler(args), args)
