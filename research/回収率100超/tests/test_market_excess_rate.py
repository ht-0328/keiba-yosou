"""市場の期待に対する超過成績のテスト。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd
import pytest

from 回収率100超.analysis.feature import MarketExcessRate


def _runs(actual: list[int], expected: list[float], rider: str = "A") -> pd.DataFrame:
    """同じ騎手が順に乗った出走の表。"""
    return pd.DataFrame({
        "race_date": pd.to_datetime([f"2026-01-{day + 1:02d}" for day in range(len(actual))]),
        "race_no": 1, "horse_no": 1, "jockey_code": rider,
        "placed": actual, "期待": expected,
    })


def test_最初の出走はまだ実績が無いので0に近い() -> None:
    excess = MarketExcessRate(shrink=10.0).build(_runs([1, 1, 1], [0.3, 0.3, 0.3]),
                                                 "jockey_code", "placed", "期待")
    assert excess.iloc[0] == pytest.approx(0.0)


def test_市場の期待より来ていれば正の値になる() -> None:
    excess = MarketExcessRate(shrink=1.0).build(_runs([1, 1, 1], [0.2, 0.2, 0.2]),
                                                "jockey_code", "placed", "期待")
    assert excess.iloc[2] > 0


def test_市場の期待より来ていなければ負の値になる() -> None:
    excess = MarketExcessRate(shrink=1.0).build(_runs([0, 0, 0], [0.5, 0.5, 0.5]),
                                                "jockey_code", "placed", "期待")
    assert excess.iloc[2] < 0


def test_自分の結果は自分の特徴量に入らない() -> None:
    """3走目だけ結果が違っても、3走目の値は変わらない（先読みしていない）。"""
    common = {"group_column": "jockey_code", "actual_column": "placed", "expected_column": "期待"}
    hit = MarketExcessRate(shrink=1.0).build(_runs([1, 0, 1], [0.3, 0.3, 0.3]), **common)
    miss = MarketExcessRate(shrink=1.0).build(_runs([1, 0, 0], [0.3, 0.3, 0.3]), **common)
    assert hit.iloc[2] == pytest.approx(miss.iloc[2])


def test_騎手が違えば別々に数える() -> None:
    frame = pd.concat([_runs([1, 1], [0.2, 0.2], rider="A"),
                       _runs([0, 0], [0.5, 0.5], rider="B")], ignore_index=True)
    excess = MarketExcessRate(shrink=1.0).build(frame, "jockey_code", "placed", "期待")
    assert excess.iloc[1] > 0
    assert excess.iloc[3] < 0


def test_出走数が少ないほど0に引き寄せられる() -> None:
    frame = _runs([1, 1], [0.2, 0.2])
    weak = MarketExcessRate(shrink=100.0).build(frame, "jockey_code", "placed", "期待")
    strong = MarketExcessRate(shrink=1.0).build(frame, "jockey_code", "placed", "期待")
    assert abs(weak.iloc[1]) < abs(strong.iloc[1])
