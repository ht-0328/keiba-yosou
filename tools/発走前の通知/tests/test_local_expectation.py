"""LocalExpectation（地方の1レースの期待度）のテスト。値は架空。"""

from __future__ import annotations

import pytest

from 地方の推奨買目.recommendation import Recommendation
from 地方の推奨買目.recommendation_set import RecommendationSet

from 発走前の通知.local_expectation import LocalExpectation


def _set(*values: float, reason: str = "") -> RecommendationSet:
    return RecommendationSet(tuple(Recommendation("単勝", (number,), 5.0, value / 5.0, value) for number, value in enumerate(values, start=1)), reason)


def test_推奨買目の_期待値_引く_1_の合計から_点数と等級() -> None:
    expectation = LocalExpectation.of(_set(2.0, 1.8, 1.5))
    assert expectation.score == pytest.approx(2.30) and expectation.grade == "A"   # 1.0 ＋ 0.8 ＋ 0.5
    assert expectation.text() == "期待度 A（点数 2.30）" and expectation.badge() == "期待度 A"
    assert LocalExpectation.of(_set(2.5, 2.0, 1.8)).grade == "S"          # 3.3
    low = LocalExpectation.of(_set(1.1, 1.2))
    assert low.score == pytest.approx(0.30) and low.grade == "C" and low.text() == "期待度 C（点数 0.30）"


def test_推奨買目が無ければ_なしと理由() -> None:
    none = LocalExpectation.of(_set(reason="期待値が線に届く組が無い"))
    assert none.score is None and none.grade is None and none.badge() == ""
    assert none.text() == "期待度 なし（推奨買目が無い: 期待値が線に届く組が無い）"
    assert LocalExpectation.of(_set()).text() == "期待度 なし（推奨買目が無い）"


def test_前日の時点は出さない理由を書く() -> None:
    expectation = LocalExpectation.not_race_day()
    assert expectation.grade is None and expectation.badge() == ""
    assert expectation.text() == "期待度 なし（馬体重が届く前の前日の時点では出さない。当日の時点で出す）"
