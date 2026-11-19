"""LocalExpectation（地方の1レースの期待度）のテスト。値は架空。"""

from __future__ import annotations

import pytest

from 地方の直前の買い目.late_bets import LateBets
from 地方の直前の買い目.late_pick import LatePick

from 発走前の通知.local_expectation import LocalExpectation


def test_直前の買い目の線への近さから_点数と等級() -> None:
    bought = LocalExpectation.of(LateBets((LatePick(3, 14.2, 0.5, 1.1, (1, 2)),), "", "11191841", 1.158))
    assert bought.score == pytest.approx(1.158) and bought.grade == "S"
    assert bought.text() == "期待度 S（点数 1.16）" and bought.badge() == "期待度 S"
    near = LocalExpectation.of(LateBets((), "2つの見込みがそろって線以上の馬がいない", "11191841", 0.91))
    assert near.grade == "A" and near.text() == "期待度 A（点数 0.91）"
    assert LocalExpectation.of(LateBets((), "", "", 0.6)).grade == "B" and LocalExpectation.of(LateBets((), "", "", 0.3)).grade == "C"


def test_見込みを出せなければ_なしと理由() -> None:
    none = LocalExpectation.of(LateBets.none("時系列オッズの断面がまだ無い"))
    assert none.score is None and none.grade is None and none.badge() == ""
    assert none.text() == "期待度 なし（見込みを出せない: 時系列オッズの断面がまだ無い）"
    assert LocalExpectation.of(None).text() == "期待度 なし（見込みを出せない）"


def test_前日の時点は出さない理由を書く() -> None:
    expectation = LocalExpectation.not_race_day()
    assert expectation.grade is None and expectation.badge() == ""
    assert expectation.text() == "期待度 なし（馬体重が届く前の前日の時点では出さない。当日の時点で出す）"
