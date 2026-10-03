"""MarkReport（いつも同じ形の成績の表）と PopularityBaseline（同じ人気の馬全体）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd
import pytest

from 印の成績.mark_report import MarkReport
from 印の成績.popularity_baseline import PopularityBaseline

#: 2レース・各4頭。（印, 人気, 着順, 単勝払戻, 複勝払戻, 危険）。A は期待度「高」、B は「低」。
_RACE_A = [("◎", 2, 1, 500, 200, False), ("○", 1, 4, 0, 0, False), ("▲", 3, 2, 0, 150, False), ("消", 4, 3, 0, 300, False)]
_RACE_B = [("消", 1, 1, 200, 110, True), ("◎", 2, 2, 0, 130, False), ("○", 3, 5, 0, 0, False), ("▲", 4, 3, 0, 250, False)]
_EXPECTATION = {"A": "高", "B": "低"}


def _marked() -> pd.DataFrame:
    rows = []
    for race_id, date, fold, race in (("A", "2024-01-06", "2024年前半", _RACE_A), ("B", "2025-07-05", "2025年後半", _RACE_B)):
        for mark, popularity, finish, win, place, danger in race:
            rows.append({"race_id": race_id, "race_date": pd.Timestamp(date), "fold": fold, "mark": mark,
                         "popularity": float(popularity), "finish": float(finish), "win_payout": win, "place_payout": place,
                         "is_danger": danger, "expectation": _EXPECTATION[race_id]})
    return pd.DataFrame(rows)


def test_いつも同じ6つの表を同じ見出しで出す() -> None:
    tables = MarkReport().tables(_marked(), "条件。", {"2025年後半": {"1番人気": 0.12}})
    assert [table.title[:2] for table in tables] == ["1.", "2.", "3.", "4.", "5.", "6."]
    marks = {row[0]: row for row in tables[0].rows if not row[0].startswith("└")}
    assert marks["◎"][2:4] == ["2", "1-1-0-0"] and marks["◎"][4] == "50.0%"  # 勝率
    assert marks["◎（1番人気以外）"][2] == "2" and marks["◎（1番人気）"][2] == "0"
    assert marks["消のうち 危険な1番人気"][3] == "1-0-0-0"
    assert marks["◎（期待度 高）"][3] == "1-0-0-0" and marks["◎（期待度 低）"][3] == "0-1-0-0"
    assert "◎が1番人気以外だったレース 100.0%" in tables[0].note


def test_上位3つの印の来た頭数と2頭の組() -> None:
    tables = MarkReport().tables(_marked(), "条件。")
    counts = {row[0]: row for row in tables[1].rows}
    # A は ◎▲ の2頭、B は ◎ の1頭（▲ は3着だが、○ は5着・◎ は2着 → ◎▲ の2頭）
    assert counts["◎○▲"][1:] == ["0.0%", "0.0%", "100.0%", "0.0%", "100.0%", "100.0%"]
    # 1〜3番人気: A は 2・3番人気が来て2頭、B は 1・2番人気が来て2頭
    assert counts["1〜3番人気"][5] == "100.0%"
    pairs = {row[0]: row[1] for row in tables[2].rows}
    assert pairs == {"◎と○": "0.0%", "◎と▲": "100.0%", "○と▲": "0.0%"}


def test_区切りごとの危険の線と期待度が高のレース数() -> None:
    folds = MarkReport().tables(_marked(), "条件。", {"2025年後半": {"1番人気": 0.12}})[4]
    assert folds.rows == [["2024年前半", "1", "0", "—", "1"], ["2025年後半", "1", "1", "12ポイント", "0"]]


def test_二重丸の期待度ごとの単勝の成績() -> None:
    table = MarkReport().tables(_marked(), "条件。")[5]
    rows = {row[0]: row for row in table.rows}
    assert list(rows) == ["高", "低", "◎ 全体"]
    # 高: A の ◎（1着・払戻 500円）が1頭。開催日は2日なので 1開催日あたり 0.50
    assert rows["高"][1:6] == ["1", "0.50", "1-0-0-0", "100.0%", "500.0%"]
    assert rows["低"][1] == "1" and rows["低"][5] == "0.0%"
    assert rows["◎ 全体"][1] == "2" and rows["◎ 全体"][5] == "250.0%"
    assert "〜" in rows["高"][6]  # 90% の幅


def test_同じ人気の馬全体は人気の内訳で重み付けする() -> None:
    everyone = pd.DataFrame({"popularity": [1, 1, 2, 2], "finish": [1, 4, 2, 5], "win_payout": [200, 0, 0, 0],
                             "place_payout": [110, 0, 150, 0]})
    chosen = pd.DataFrame({"popularity": [1, 2, 2, 2]})
    rates = PopularityBaseline(everyone).rates(chosen)
    # 1番人気の勝率 0.5 × 0.25 + 2番人気の勝率 0 × 0.75
    assert rates["勝率"] == pytest.approx(0.125)
    assert rates["複勝率"] == pytest.approx(0.5)
