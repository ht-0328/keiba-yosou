"""レースの目安の等級（``race_grade``）のテスト。値は架空。"""

from __future__ import annotations

from ..race_grade import GRADES, LOWER_LINES, GradeScale


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
