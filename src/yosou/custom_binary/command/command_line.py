"""python -m yosou.custom_binary の入口。"""

import argparse
from collections.abc import Sequence

from 共通 import cli

from .evaluate_command import EvaluateCommand
from .features_command import FeaturesCommand
from .predict_command import PredictCommand
from .train_command import TrainCommand


class CommandLine:
    """引数を読み、サブコマンド（features・train・predict・evaluate）を実行し、結果の表を出す。"""

    def __init__(self) -> None:
        self._commands = (FeaturesCommand(), TrainCommand(), PredictCommand(), EvaluateCommand())

    def run(self, argv: Sequence[str] | None = None) -> None:
        cli.run(self.parser(), self._execute, argv)

    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="YAMLと特徴量テキストで設定する予想モデル", allow_abbrev=False)
        commands = parser.add_subparsers(dest="command", required=True)
        for command in self._commands:
            command.add_parser(commands)
        return parser

    def _execute(self, args: argparse.Namespace) -> None:
        cli.emit(args.handler(args), args)
