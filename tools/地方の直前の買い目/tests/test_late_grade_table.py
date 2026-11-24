"""LateGradeTable（期待度ごとの、線にいちばん近い馬の単勝の成績）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from 地方の直前の買い目 import late_columns as c
from 地方の直前の買い目.late_grade_table import LateGradeTable


def _scored() -> pd.DataFrame:
    rows = [
        # レース A（2024年）: 2番が線以上（S）。勝って 1,500円
        ("A", "2024-07-01", 1, 0.10, 0.80), ("A", "2024-07-01", 2, 0.50, 1.10),
        # レース B（2024年）: いちばん近いのは 1番の 0.86（A）。外れ
        ("B", "2024-07-02", 1, 0.30, 0.95), ("B", "2024-07-02", 2, 0.10, 0.90),
        # レース C（2025年）: 1番の 0.69（B）。勝って 400円
        ("C", "2025-01-05", 1, 0.24, 1.00), ("C", "2025-01-05", 2, 0.05, 0.70),
        # レース D（2025年）: 2番の 0.29（C）。外れ
        ("D", "2025-01-06", 1, 0.05, 0.50), ("D", "2025-01-06", 2, 0.10, 0.60),
        # レース E: 払戻の表に無い（数えない）
        ("E", "2025-01-07", 1, 0.90, 1.50),
    ]
    return pd.DataFrame(rows, columns=[c.RACE_ID, c.RACE_DATE, c.HORSE_NO, c.LIKENESS, c.PAYBACK])


def _wins() -> pd.DataFrame:
    return pd.DataFrame({"race_id": ["A", "B", "C", "D"], "horse_no": [2, 2, 1, 1], "payout": [1500, 300, 400, 250]})


def test_レースごとに線にいちばん近い馬を選び_その値で等級を付ける() -> None:
    races = LateGradeTable().races(_scored(), _wins()).set_index(c.RACE_ID)
    assert list(races.index) == ["A", "B", "C", "D"]                       # E は結果が無いので数えない
    assert races[c.HORSE_NO].tolist() == [2, 1, 1, 2] and races["grade"].tolist() == ["S", "A", "B", "C"]
    assert races["payout"].tolist() == [1500.0, 0.0, 400.0, 0.0]


def test_表は_全体と年ごとに_等級の行を並べる() -> None:
    table = LateGradeTable().table(_scored(), _wins(), "題")
    assert table.rows[0] == ["全体", "S", 1, "25.0%", "100.0%", "1500.0%"]
    assert table.rows[1] == ["全体", "A", 1, "25.0%", "0.0%", "0.0%"]
    assert table.rows[4] == ["2024年", "S", 1, "50.0%", "100.0%", "1500.0%"]
    assert table.rows[6] == ["2024年", "B", 0, "—", "—", "—"]
    assert table.rows[10] == ["2025年", "B", 1, "50.0%", "100.0%", "400.0%"]
