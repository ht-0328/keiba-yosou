"""時点（木曜・前日・当日）の選び方のテスト。DB の材料を段階的に足して、選ばれる時点が進むことを確かめる。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db
from 共通.tests.test_race_signals import CARD_RID, NAME_LIST_RID, build
from 今週の予想.timing_chooser import TimingChooser


def choose(path: Path, rid: str) -> str:
    with db.open_db(path) as con:
        return TimingChooser().choose(con, rid).timing.label


def test_オッズが無ければ木曜(tmp_path: Path) -> None:
    path = build(tmp_path / "a.duckdb")
    assert choose(path, NAME_LIST_RID) == "木曜" and choose(path, CARD_RID) == "木曜"


def test_オッズがあっても馬番が未定なら木曜で_出馬表なら前日(tmp_path: Path) -> None:
    path = build(tmp_path / "b.duckdb", odds=True)
    assert choose(path, NAME_LIST_RID) == "木曜"
    assert choose(path, CARD_RID) == "前日"


def test_馬体重と馬場状態も出ていれば当日_片方だけなら前日(tmp_path: Path) -> None:
    assert choose(build(tmp_path / "c.duckdb", odds=True, weights=True, going=True), CARD_RID) == "当日"
    assert choose(build(tmp_path / "d.duckdb", odds=True, weights=True), CARD_RID) == "前日"
    assert choose(build(tmp_path / "e.duckdb", odds=True, going=True), CARD_RID) == "前日"


def test_無いレースは見つからないと言う(tmp_path: Path) -> None:
    with db.open_db(build(tmp_path / "f.duckdb")) as con:
        with pytest.raises(LookupError):
            TimingChooser().choose(con, "2025041905010109")
