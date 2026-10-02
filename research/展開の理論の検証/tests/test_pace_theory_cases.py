"""ペースの区分・レースの表・事例の選び方のテスト。架空の値だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 展開の理論の検証.analysis.cases import PATTERNS, CasePicker
from 展開の理論の検証.analysis.pace import (
    HIGH,
    MIDDLE,
    NO_BASELINE,
    PACE,
    SLOW,
    WINNER_STYLE,
    RacePaceClassifier,
    RaceTable,
)


def _races(first3f_last: float) -> pd.DataFrame:
    """同じコース・クラスで、前半 35.0秒の前後のレースが 40 あり、最後の1レースの前半が ``first3f_last``。"""
    count = 41
    first3f = 35.0 + np.tile([-0.5, 0.5], count // 2 + 1)[:count]
    first3f[-1] = first3f_last
    return pd.DataFrame({
        "race_id": [f"R{i:03d}" for i in range(count)],
        "race_date": pd.date_range("2024-01-01", periods=count, freq="7D"),
        "venue_code": "05", "track_code": "23", "distance_m": 1600, "class_order": 3,
        "first3f": first3f, "last3f_race": 36.0,
    })


def _pace_of_last(first3f_last: float) -> str:
    return RacePaceClassifier().classify(_races(first3f_last))[PACE].iloc[-1]


def test_基準より標準偏差の半分以上速ければハイ() -> None:
    assert _pace_of_last(34.0) == HIGH


def test_基準より標準偏差の半分以上遅ければスロー() -> None:
    assert _pace_of_last(36.0) == SLOW


def test_基準の前後ならミドル() -> None:
    assert _pace_of_last(35.1) == MIDDLE


def test_前の3年に30レースなければ基準なし() -> None:
    assert RacePaceClassifier().classify(_races(34.0))[PACE].iloc[0] == NO_BASELINE


def test_レースの表は勝ち馬の脚質を持ち_同着は馬番の小さい方() -> None:
    runners = pd.DataFrame({
        "race_id": ["A", "A", "A"], "horse_no": [5, 2, 7], "finish": [1, 1, 3],
        "style": ["差し", "逃げ", "先行"], "style_before": ["差し", "先行", None],
        **{column: 0 for column in ("race_date", "year", "venue_code", "venue", "race_no", "race_name", "track_code",
                                    "surface", "course", "distance_m", "condition", "class_name", "class_order",
                                    "grade_code", "field_size", "lead_candidates", "first3f", "last3f_race")},
    })
    races = RaceTable().build(runners)
    assert len(races) == 1
    assert races[WINNER_STYLE].iloc[0] == "逃げ"


def test_事例は型に当てはまるレースだけから選び_数を超えない() -> None:
    races = pd.DataFrame({
        "race_id": list("ABCD"), "race_date": pd.date_range("2025-01-01", periods=4),
        PACE: [HIGH, HIGH, SLOW, HIGH], WINNER_STYLE: ["逃げ", "差し", "逃げ", "先行"], "lead_candidates": [0, 0, 3, 2],
    })
    high_front = next(pattern for pattern in PATTERNS if pattern.key == "high_front")
    picked = CasePicker(count=5, seed=0).pick(races, high_front)
    assert list(picked["race_id"]) == ["A", "D"]


def test_同じ種なら同じ事例を選ぶ() -> None:
    races = pd.DataFrame({
        "race_id": [f"R{i}" for i in range(30)], "race_date": pd.date_range("2025-01-01", periods=30),
        PACE: HIGH, WINNER_STYLE: "逃げ", "lead_candidates": 0,
    })
    pattern = PATTERNS[3]
    first = CasePicker(count=5, seed=1).pick(races, pattern)["race_id"].tolist()
    second = CasePicker(count=5, seed=1).pick(races, pattern)["race_id"].tolist()
    assert first == second
