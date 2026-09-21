"""血統成績のコマンドの入口（引数の受け取りと出力）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from 合成DB import synth

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 血統成績 import pedigree as command  # noqa: E402


def _run(argv: list[str], capsys) -> str:
    with pytest.raises(SystemExit) as stopped:
        from 共通 import cli
        cli.run(command.build_parser(), command.main, argv)
    assert stopped.value.code == 0
    return capsys.readouterr().out


def test_list_shows_roles_splits_and_sorts(capsys):
    out = _run(["--list"], capsys)
    assert "父の父" in out and "距離帯" in out and "条件の平均との差" in out


def test_split_table_is_printed(synth_db: Path, capsys):
    out = _run(["--split", "芝ダ", "--min-runs", "1", "--min-split-runs", "1", "--db", str(synth_db)], capsys)
    assert "父の産駒の成績（芝ダ別）" in out and "条件の平均との差" in out


def test_sort_by_baseline_edge_is_accepted(synth_db: Path, capsys):
    out = _run(["--split", "競馬場", "--sort", "条件の平均との差", "--min-runs", "1",
                "--min-split-runs", "1", "--db", str(synth_db)], capsys)
    assert "父の産駒の成績（競馬場別）" in out


def test_all_prints_one_table_per_split(synth_db: Path, capsys):
    out = _run(["--all", "--min-runs", "1", "--min-split-runs", "1", "--db", str(synth_db)], capsys)
    for split_name in command.ALL_SPLITS:
        assert f"（{split_name}別）" in out


def test_overall_prints_one_table(synth_db: Path, capsys):
    out = _run(["--overall", "--min-runs", "1", "--db", str(synth_db)], capsys)
    assert "父の産駒の成績（全体）" in out and "条件の平均との差" not in out


def test_unknown_name_exits_with_one_line(synth_db: Path, capsys):
    from 共通 import cli
    with pytest.raises(SystemExit) as stopped:
        cli.run(command.build_parser(), command.main,
                ["--name", "居ない父", "--min-runs", "1", "--db", str(synth_db)])
    assert stopped.value.code == cli.EXIT_ERROR and "産駒" in capsys.readouterr().err
