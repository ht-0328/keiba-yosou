"""コマンドの引数を確かめる。"""

from __future__ import annotations

import pytest

from ..command.command_line import CommandLine

#: サブコマンドごとの、必須の引数を満たす最小の書き方。
_MINIMAL_ARGS = {
    "train": ["train"],
    "predict": ["predict", "2026100404050311", "--timing", "当日"],
    "backtest": ["backtest"],
}


@pytest.mark.parametrize("name", list(_MINIMAL_ARGS))
def test_every_command_has_output_options(name: str) -> None:
    """結果の表を出す ``cli.emit`` が使う ``--format``・``--out`` を、どのサブコマンドも持つ。"""
    args = CommandLine()._parser().parse_args(_MINIMAL_ARGS[name])
    assert args.format and args.out is None


def test_predict_accepts_odds() -> None:
    args = CommandLine()._parser().parse_args([*_MINIMAL_ARGS["predict"], "--odds", "3:2.4", "7:5.1"])
    assert args.odds == ["3:2.4", "7:5.1"]
