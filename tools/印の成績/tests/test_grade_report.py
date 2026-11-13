"""期待度ごとの ◎ の成績の表（GradeReport）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from 印の成績.grade_report import GradeReport

#: 4レース。◎ の点数（1着の確率 ＋ 期待値 − 1）は S（0.5 + 0.9 − 1 = 0.4）・A（0.3 + 0.9 − 1 = 0.2）・B（0.2 + 0.85 − 1 = 0.05）・C（0.1 + 0.8 − 1 = −0.1）。
#: （印, 1着の確率, 期待値, 人気, 着順, 単勝払戻, 複勝払戻）。
_RACES = {
    "A": [("◎", 0.50, 0.90, 1, 1, 200, 110), ("○", 0.20, 0.8, 2, 2, 0, 150)],
    "B": [("◎", 0.30, 0.90, 2, 4, 0, 0), ("○", 0.25, 0.8, 1, 1, 180, 120)],
    "C": [("◎", 0.20, 0.85, 5, 3, 0, 300), ("○", 0.30, 0.8, 1, 2, 0, 110)],
    "D": [("◎", 0.10, 0.80, 3, 6, 0, 0), ("○", 0.35, 0.8, 1, 1, 150, 110)],
}


def _marked(with_values: bool = True) -> pd.DataFrame:
    rows = []
    for race_id, horses in _RACES.items():
        for mark, probability, value, popularity, finish, win, place in horses:
            row = {"race_id": race_id, "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半", "mark": mark,
                   "probability": probability + 0.1, "popularity": float(popularity), "finish": float(finish), "win_payout": win, "place_payout": place}
            if with_values:
                row.update({"win_probability": probability, "win_value": value})
            rows.append(row)
    return pd.DataFrame(rows)


def test_ランクごとに二重丸の成績と割合を並べ_無いランクは0で出す() -> None:
    table = GradeReport().table(_marked())
    assert table.title == "13. 期待度ごとの ◎ の単勝・複勝の成績"
    assert table.columns[:4] == ["期待度", "レース数", "レースの割合", "着別度数"]
    assert table.columns[-4:] == ["同じ人気の馬全体の勝率", "同じ人気の馬全体の単勝回収率", "同じ人気の馬全体の複勝率", "同じ人気の馬全体の複勝回収率"]
    rows = {row[0]: row for row in table.rows}
    assert list(rows) == ["S", "A", "B", "C", "◎ 全体"]
    assert rows["S"][1:4] == ["1", "25.0%", "1-0-0-0"] and rows["S"][4] == "100.0%"   # 勝率
    assert rows["A"][1:4] == ["1", "25.0%", "0-0-0-1"]
    assert rows["B"][1:4] == ["1", "25.0%", "0-0-1-0"] and rows["B"][6] == "100.0%"   # 複勝率
    assert rows["C"][1:4] == ["1", "25.0%", "0-0-0-1"]
    assert rows["◎ 全体"][1:3] == ["4", "100.0%"]
    assert "S 0.35 以上・A 0.15 以上・B 0 以上・C 0 未満" in table.note


def test_1着の予想が無ければどのランクにも入らない() -> None:
    rows = {row[0]: row for row in GradeReport().table(_marked(with_values=False)).rows}
    assert all(rows[grade][1] == "0" for grade in "SABC") and rows["◎ 全体"][1] == "4"


def test_地方は期待度の決め方で分ける() -> None:
    from yosou.shared.race_grade import EXPECTATION_LABEL, EXPECTATION_MEANING, LocalExpectationScale

    table = GradeReport(LocalExpectationScale(), EXPECTATION_LABEL, EXPECTATION_MEANING).table(_marked())
    assert table.title == "13. 期待度ごとの ◎ の単勝・複勝の成績" and table.columns[0] == "期待度"
    rows = {row[0]: row for row in table.rows}
    # 点数は 1着の確率 ＋ 3 ×（期待値 − 1）: A 0.5 − 0.3 = 0.20（A）・B 0.3 − 0.3 = 0.00（B）・C 0.2 − 0.45 = −0.25（C）・D 0.1 − 0.6 = −0.5（C）
    assert [rows[grade][1] for grade in "SABC"] == ["0", "1", "1", "2"]
    assert "S 0.45 以上・A 0.15 以上・B -0.1 以上・C -0.1 未満" in table.note and "期待度が高いほど" in table.note
