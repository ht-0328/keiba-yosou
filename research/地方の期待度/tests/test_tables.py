"""年 × 等級の表（GradeYearTable）と推奨買目の表（RecommendedTickets）を、架空の値で確かめる。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 地方の期待度.analysis.grade_year_table import GradeYearTable
from 地方の期待度.analysis.recommended_tickets import RecommendedTickets

#: 等級ごとに4レース（着順, 単勝払戻, 複勝払戻）。2024年は 勝率・複勝率・単勝回収率・複勝回収率 の4つとも C → S の順に上がる。
_PLAN = {
    "S": [(1, 200, 110), (1, 200, 110), (1, 200, 110), (2, 0, 110)],
    "A": [(1, 200, 110), (1, 200, 110), (3, 0, 110), (4, 0, 0)],
    "B": [(1, 200, 110), (3, 0, 110), (4, 0, 0), (5, 0, 0)],
    "C": [(3, 0, 110), (4, 0, 0), (5, 0, 0), (6, 0, 0)],
}


def _graded() -> pd.DataFrame:
    """2024年は上の形、2025年は S だけ全部外れる（S が C より下になる）。"""
    rows = []
    for year in (2024, 2025):
        for grade, results in _PLAN.items():
            for index, (finish, win, place) in enumerate(results):
                if year == 2025 and grade == "S":
                    finish, win, place = 9, 0, 0
                rows.append({"race_id": f"{year}{grade}{index}", "year": year, "grade": grade, "finish": float(finish),
                             "win_payout": win, "place_payout": place})
    return pd.DataFrame(rows)


def test_年ごとに等級の行と全体の行を並べる() -> None:
    table = GradeYearTable().table(_graded(), "試し")
    assert table.columns == ["年", "期待度", "レース数", "レースの割合", "勝率", "複勝率", "単勝回収率", "複勝回収率"]
    rows = {(row[0], row[1]): row for row in table.rows}
    assert rows[("2024", "S")][2:] == ["4", "25.0%", "75.0%", "100.0%", "150.0%", "110.0%"]
    assert rows[("2024", "C")][2:] == ["4", "25.0%", "0.0%", "25.0%", "0.0%", "27.5%"]
    assert rows[("2024", "全体")][2] == "16"
    assert rows[("2025", "S")][4] == "0.0%"


def test_等級の順に上がった年を率ごとに数える() -> None:
    years = GradeYearTable().monotone_years(_graded())
    assert years == {"勝率": [2024], "複勝率": [2024], "単勝回収率": [2024], "複勝回収率": [2024]}
    assert GradeYearTable().monotone_years(_graded(), years=[2025]) == {"勝率": [], "複勝率": [], "単勝回収率": [], "複勝回収率": []}


def test_推奨買目はレースにまとめて_等級ごとの回収率と的中レース率(tmp_path: Path) -> None:
    csv = tmp_path / "買い目.csv"
    pd.DataFrame({"race_id": ["2024S0", "2024S0", "2024A0", "2025C1"], "payout": [0, 450, 0, 0], "券種": ["単勝", "複勝", "単勝", "単勝"]}).to_csv(csv, index=False)
    tickets = RecommendedTickets(csv)
    assert tickets.available() and not RecommendedTickets(tmp_path / "無い.csv").available()
    table = tickets.table(_graded(), "試し")
    rows = {(row[0], row[1]): row for row in table.rows}
    assert rows[("2024", "S")][2:] == ["1", "2.0", "225.0%", "100.0%"]
    assert rows[("2024", "A")][2:] == ["1", "1.0", "0.0%", "0.0%"]
    assert rows[("2024", "B")][2:] == ["0", "—", "—", "—"]
    assert rows[("2025", "全体")][2] == "1"
