"""レースの目安の等級（``race_grade``）のテスト。値は架空。"""

from __future__ import annotations

import pytest

from ..race_grade import (
    EXPECTATION_LINES,
    GRADES,
    LOWER_LINES,
    RANK_LINES,
    VALUE_WEIGHT,
    GradeScale,
    LocalExpectationScale,
    TopRankScale,
)


def test_grade_scale_uses_the_fixed_lines_including_the_lower_end() -> None:
    scale = GradeScale()
    assert GRADES == ("S", "A", "B", "C") and LOWER_LINES == {"S": 0.75, "A": 0.50, "B": 0.25, "C": 0.0}
    assert scale.of(1.0) == "S" and scale.of(0.75) == "S"
    assert scale.of(0.7499) == "A" and scale.of(0.5) == "A"
    assert scale.of(0.49) == "B" and scale.of(0.25) == "B"
    assert scale.of(0.2499) == "C" and scale.of(0.0) == "C"


def test_grade_scale_has_no_grade_without_a_probability() -> None:
    scale = GradeScale()
    assert scale.of(None) is None and scale.of(float("nan")) is None


def test_legend_names_every_line() -> None:
    assert GradeScale.legend() == "S 75% 以上・A 50% 以上・B 25% 以上・C 25% 未満"


def test_top_rank_is_the_sum_of_win_probability_and_value_edge() -> None:
    scale = TopRankScale()
    assert RANK_LINES["S"] == 0.35 and RANK_LINES["A"] == 0.15 and RANK_LINES["B"] == 0.0
    assert TopRankScale.score(0.3, 1.05) == pytest.approx(0.35) and TopRankScale.score(0.3, None) is None and TopRankScale.score(None, 1.0) is None
    assert scale.of(0.35) == "S" and scale.of(0.34) == "A" and scale.of(0.15) == "A" and scale.of(0.0) == "B" and scale.of(-0.01) == "C"
    assert scale.of(None) is None and scale.of(float("nan")) is None
    assert TopRankScale.legend().endswith("S 0.35 以上・A 0.15 以上・B 0 以上・C 0 未満")


def test_local_expectation_weights_the_value_edge_three_times() -> None:
    scale = LocalExpectationScale()
    assert VALUE_WEIGHT == 3.0 and EXPECTATION_LINES["S"] == 0.45 and EXPECTATION_LINES["A"] == 0.15 and EXPECTATION_LINES["B"] == -0.10
    assert LocalExpectationScale.score(0.30, 1.05) == pytest.approx(0.45)      # 0.30 + 3 × 0.05
    assert LocalExpectationScale.score(0.20, 0.90) == pytest.approx(-0.10)     # 0.20 − 3 × 0.10
    assert LocalExpectationScale.score(0.3, None) is None and LocalExpectationScale.score(None, 1.0) is None
    assert LocalExpectationScale.score(float("nan"), 1.0) is None
    assert scale.of(0.45) == "S" and scale.of(0.449) == "A" and scale.of(0.15) == "A" and scale.of(0.149) == "B"
    assert scale.of(-0.10) == "B" and scale.of(-0.101) == "C" and scale.of(None) is None and scale.of(float("nan")) is None
    assert LocalExpectationScale.legend() == "期待度の点数は ◎ の1着の確率 ＋ 3 ×（単勝の期待値 − 1）。S 0.45 以上・A 0.15 以上・B -0.1 以上・C -0.1 未満"
