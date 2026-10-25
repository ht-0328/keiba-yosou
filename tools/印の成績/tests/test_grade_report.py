"""的中率の等級ごとの ◎ の成績の表（GradeReport）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from 印の成績.grade_report import GradeReport

#: 4レース。◎ の3着以内の確率は S（0.8）・A（0.5）・B（0.3）・B（0.26）。（印, 確率, 人気, 着順, 単勝払戻, 複勝払戻）。
_RACES = {
    "A": [("◎", 0.80, 1, 1, 200, 110), ("○", 0.40, 2, 2, 0, 150)],
    "B": [("◎", 0.50, 2, 4, 0, 0), ("○", 0.45, 1, 1, 180, 120)],
    "C": [("◎", 0.30, 5, 3, 0, 300), ("○", 0.55, 1, 2, 0, 110)],
    "D": [("◎", 0.26, 3, 6, 0, 0), ("○", 0.60, 1, 1, 150, 110)],
}


def _marked() -> pd.DataFrame:
    rows = []
    for race_id, horses in _RACES.items():
        for mark, probability, popularity, finish, win, place in horses:
            rows.append({"race_id": race_id, "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半", "mark": mark,
                         "probability": probability, "popularity": float(popularity), "finish": float(finish),
                         "win_payout": win, "place_payout": place})
    return pd.DataFrame(rows)


def test_等級ごとに二重丸の成績と割合を並べ_無い等級は0で出す() -> None:
    table = GradeReport().table(_marked())
    assert table.title == "13. 的中率の等級ごとの ◎ の成績"
    assert table.columns[:4] == ["的中率の等級", "レース数", "レースの割合", "着別度数"]
    assert table.columns[-2:] == ["同じ人気の馬全体の複勝率", "同じ人気の馬全体の複勝回収率"]
    rows = {row[0]: row for row in table.rows}
    assert list(rows) == ["S", "A", "B", "C", "◎ 全体"]
    assert rows["S"][1:4] == ["1", "25.0%", "1-0-0-0"] and rows["S"][6] == "100.0%"   # 複勝率
    assert rows["A"][1:4] == ["1", "25.0%", "0-0-0-1"]
    assert rows["B"][1:4] == ["2", "50.0%", "0-0-1-1"] and rows["B"][6] == "50.0%"
    assert rows["C"][1:4] == ["0", "0.0%", "0-0-0-0"] and rows["C"][4] == "—"
    assert rows["◎ 全体"][1:3] == ["4", "100.0%"]
    assert "等級は S 75% 以上・A 50% 以上・B 25% 以上・C 25% 未満" in table.note
