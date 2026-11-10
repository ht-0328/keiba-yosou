"""期待度の線の決め方（GradeLines）と点数の候補（ScoreCandidate）を、架空の値で確かめる。"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from 地方の期待度.analysis.grade_lines import GradeLines
from 地方の期待度.analysis.score_candidate import CANDIDATES, ScoreCandidate


def test_線は決める年の分位で_上から2割_3割_3割_残りになる() -> None:
    scores = pd.Series([i / 100 for i in range(1, 101)])   # 0.01〜1.00
    lines = GradeLines().decide(scores)
    assert lines["S"] == pytest.approx(0.8, abs=0.011) and lines["A"] == pytest.approx(0.5, abs=0.011) and lines["B"] == pytest.approx(0.2, abs=0.011)
    assert lines["C"] == -math.inf
    graded = GradeLines.grade(scores, lines)
    shares = graded.value_counts(normalize=True)
    assert shares["S"] == pytest.approx(0.2, abs=0.02) and shares["A"] == pytest.approx(0.3, abs=0.02)
    assert shares["B"] == pytest.approx(0.3, abs=0.02) and shares["C"] == pytest.approx(0.2, abs=0.02)


def test_等級は線の下の値を含み_欠損は無し() -> None:
    lines = {"S": 0.35, "A": 0.15, "B": 0.0, "C": -math.inf}
    graded = GradeLines.grade(pd.Series([0.35, 0.349, 0.15, 0.0, -0.01, float("nan")]), lines)
    assert list(graded[:5]) == ["S", "A", "A", "B", "C"] and pd.isna(graded[5])
    assert GradeLines.legend(lines) == "S 0.35 以上・A 0.15 以上・B 0 以上・C 0 未満"


def test_割合が不正なら誤り() -> None:
    with pytest.raises(ValueError):
        GradeLines((0.5, 0.5, 0.1))
    with pytest.raises(ValueError):
        GradeLines().decide(pd.Series([float("nan")]))


def test_候補の式は_確率と期待値から点数を出す() -> None:
    tops = pd.DataFrame({"win_probability": [0.3, 0.1], "win_value": [1.2, 0.9], "probability": [0.6, 0.3], "place_value": [1.1, 0.8]})
    by_key = {candidate.key: candidate for candidate in CANDIDATES}
    assert isinstance(by_key["A"], ScoreCandidate)
    assert list(by_key["A"].score(tops)) == pytest.approx([0.5, 0.0])        # 0.3 + 0.2, 0.1 − 0.1
    assert list(by_key["B"].score(tops)) == pytest.approx([0.3, 0.1])
    assert list(by_key["C"].score(tops)) == pytest.approx([0.2, -0.1])
    assert list(by_key["D"].score(tops)) == pytest.approx([0.7, -0.1])       # 0.3 + 0.4, 0.1 − 0.2
    assert list(by_key["F"].score(tops)) == pytest.approx([0.7, 0.1])        # 0.6 + 0.1, 0.3 − 0.2
    assert list(by_key["H"].score(tops)) == pytest.approx([0.36, 0.09])
    assert len({candidate.key for candidate in CANDIDATES}) == len(CANDIDATES)
