"""レースの目安の等級（``race_grade``）のテスト。値は架空。"""

from __future__ import annotations

import pytest

from ..race_grade import (
    BET_PROFIT_LINES,
    EXPECTATION_LINES,
    GRADES,
    LOWER_LINES,
    RANK_LINES,
    RANK_VALUE_WEIGHT,
    SKIP_GRADE,
    SKIP_VALUE,
    TOP_SCORE_LINES,
    TOP_SCORE_WEIGHT,
    GradeScale,
    LocalBetProfitScale,
    LocalExpectationScale,
    LocalTopScoreScale,
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


def test_top_rank_skips_low_value_and_weights_the_value_edge() -> None:
    scale = TopRankScale()
    assert RANK_VALUE_WEIGHT == 1.25 and SKIP_VALUE == 0.90 and SKIP_GRADE == "見送り"
    assert RANK_LINES["S"] == 0.28 and RANK_LINES["A"] == 0.14 and RANK_LINES["B"] == 0.02
    assert TopRankScale.score(0.3, 1.04) == pytest.approx(0.35) and TopRankScale.score(0.3, None) is None and TopRankScale.score(None, 1.0) is None
    assert scale.of(0.28) == "S" and scale.of(0.279) == "A" and scale.of(0.14) == "A" and scale.of(0.02) == "B" and scale.of(0.019) == "C"
    assert scale.of(None) is None and scale.of(float("nan")) is None
    assert scale.grade(0.50, 0.89) == "見送り" and scale.grade(0.10, 0.90) == "C" and scale.grade(0.30, 1.04) == "S"   # 線ちょうどは見送りでない
    assert scale.grade(0.3, None) is None and scale.grade(None, 1.0) is None
    assert TopRankScale.legend().startswith("◎ の単勝の期待値が 0.90 未満なら見送り")
    assert TopRankScale.legend().endswith("S 0.28 以上・A 0.14 以上・B 0.02 以上・C 0.02 未満")


def test_local_top_score_weights_the_value_edge_three_times() -> None:
    scale = LocalTopScoreScale()
    assert TOP_SCORE_WEIGHT == 3.0 and TOP_SCORE_LINES["S"] == 0.45 and TOP_SCORE_LINES["A"] == 0.15 and TOP_SCORE_LINES["B"] == -0.10
    assert LocalTopScoreScale.score(0.30, 1.05) == pytest.approx(0.45)      # 0.30 + 3 × 0.05
    assert LocalTopScoreScale.score(0.20, 0.90) == pytest.approx(-0.10)     # 0.20 − 3 × 0.10
    assert LocalTopScoreScale.score(0.3, None) is None and LocalTopScoreScale.score(None, 1.0) is None
    assert LocalTopScoreScale.score(float("nan"), 1.0) is None
    assert scale.grade(0.30, 1.05) == "S" and scale.grade(None, 1.0) is None
    assert scale.of(0.45) == "S" and scale.of(0.449) == "A" and scale.of(0.15) == "A" and scale.of(0.149) == "B"
    assert scale.of(-0.10) == "B" and scale.of(-0.101) == "C" and scale.of(None) is None and scale.of(float("nan")) is None
    assert LocalTopScoreScale.legend() == "◎の点数は ◎ の1着の確率 ＋ 3 ×（単勝の期待値 − 1）。S 0.45 以上・A 0.15 以上・B -0.1 以上・C -0.1 未満"


def test_local_expectation_grades_the_closeness_to_the_late_bet_lines() -> None:
    scale = LocalExpectationScale()
    assert EXPECTATION_LINES["S"] == 1.0 and EXPECTATION_LINES["A"] == 0.85 and EXPECTATION_LINES["B"] == 0.5
    assert scale.of(1.0) == "S" and scale.of(0.999) == "A" and scale.of(0.85) == "A" and scale.of(0.849) == "B"
    assert scale.of(0.5) == "B" and scale.of(0.49) == "C" and scale.of(-0.2) == "C" and scale.of(None) is None and scale.of(float("nan")) is None
    assert LocalExpectationScale.legend() == "期待度の点数は直前の買い目の線への近さ。S 1 以上・A 0.85 以上・B 0.5 以上・C 0.5 未満"


def test_local_bet_profit_sums_the_value_edges_of_the_recommended_tickets() -> None:
    scale = LocalBetProfitScale()
    assert BET_PROFIT_LINES["S"] == 3.2 and BET_PROFIT_LINES["A"] == 1.4 and BET_PROFIT_LINES["B"] == 0.5
    assert LocalBetProfitScale.score([1.2, 1.5, 1.05]) == pytest.approx(0.75)   # 0.2 + 0.5 + 0.05
    assert LocalBetProfitScale.score([]) is None and LocalBetProfitScale.score([float("nan")]) is None
    assert scale.grade([2.5, 2.0, 1.8]) == "S" and scale.grade([1.5, 1.5, 1.4]) == "A" and scale.grade([1.5]) == "B" and scale.grade([1.1, 1.2]) == "C"
    assert scale.of(3.2) == "S" and scale.of(3.19) == "A" and scale.of(1.4) == "A" and scale.of(0.5) == "B" and scale.of(0.49) == "C"
    assert scale.grade([]) is None and scale.of(None) is None
    assert LocalBetProfitScale.legend() == "推奨買目の期待の儲けは推奨買目の（期待値 − 1）の合計。S 3.2 以上・A 1.4 以上・B 0.5 以上・C 0.5 未満"
