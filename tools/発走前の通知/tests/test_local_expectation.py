"""LocalExpectation（地方の1レースの期待度）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd
import pytest

from 今週の予想.forecast_columns import MARK, WIN_PROBABILITY, WIN_VALUE

from 発走前の通知.local_expectation import LocalExpectation


def _table(win_value: float | None = 1.05) -> pd.DataFrame:
    return pd.DataFrame([
        {MARK: "○", WIN_PROBABILITY: 0.40, WIN_VALUE: 0.90},
        {MARK: "◎", WIN_PROBABILITY: 0.35, WIN_VALUE: win_value},
        {MARK: "－", WIN_PROBABILITY: 0.05, WIN_VALUE: 1.50},
    ])


def test_二重丸の_1着の確率と期待値から_点数と等級() -> None:
    expectation = LocalExpectation.of(_table())
    assert expectation.score == pytest.approx(0.50) and expectation.grade == "S"   # 0.35 ＋ 3 ×（1.05 − 1）
    assert expectation.text() == "期待度 S（点数 0.50）" and expectation.badge() == "期待度 S"
    low = LocalExpectation.of(_table(win_value=0.80))
    assert low.score == pytest.approx(-0.25) and low.grade == "C" and low.text() == "期待度 C（点数 -0.25）"


def test_二重丸がいないか_期待値が無ければ_なし() -> None:
    no_top = LocalExpectation.of(_table().assign(**{MARK: "○"}))
    assert no_top.score is None and no_top.grade is None and no_top.badge() == ""
    assert no_top.text() == "期待度 なし（◎ の単勝の期待値が無い）"
    no_value = LocalExpectation.of(_table(win_value=float("nan")))
    assert no_value.grade is None
    no_column = LocalExpectation.of(_table().drop(columns=[WIN_VALUE]))
    assert no_column.grade is None


def test_前日の時点は出さない理由を書く() -> None:
    expectation = LocalExpectation.not_race_day()
    assert expectation.grade is None and expectation.badge() == ""
    assert expectation.text() == "期待度 なし（馬体重が届く前の前日の時点では出さない。当日の時点で出す）"
