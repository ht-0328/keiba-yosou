"""LocalRaceMessage（地方の predict の JSON から印と買い目の文を作る）のテスト。予想の値は架空。"""

from __future__ import annotations

from datetime import datetime

from 発走前の通知.local_race_message import LocalRaceMessage
from 発走前の通知.scheduled_race import ScheduledRace

COLUMNS = ["順位", "馬番", "馬名", "単勝オッズ", "オッズから見た3着以内率", "複勝的中の確率", "複勝の期待値", "1着になる確率", "単勝の期待値",
           "3着以内に入る確率", "LightGBM", "CatBoost"]
ROWS = [
    [1, 7, "イチバン", 3.0, 0.70, 0.78, 1.10, 0.35, 1.05, 0.78, 0.77, 0.79],
    [2, 4, "ニバン", 2.7, 0.75, 0.71, 0.95, 0.27, 0.74, 0.71, 0.72, 0.70],
    [3, 8, "サンバン", 5.4, 0.55, 0.60, 1.00, 0.15, 0.81, 0.60, 0.61, 0.59],
    [4, 3, "ヨンバン", 14.2, 0.25, 0.34, 1.30, 0.06, 0.80, 0.34, 0.33, 0.35],
    [5, 2, "ゴバン", 18.3, 0.19, 0.29, 0.90, 0.04, 0.64, 0.29, 0.29, 0.29],
    [6, 1, "ロクバン", 40.0, 0.08, 0.10, 0.60, 0.01, 0.40, 0.10, 0.10, 0.10],
    [7, 6, "ナナバン", 80.0, 0.04, 0.05, 0.50, 0.005, 0.40, 0.05, 0.05, 0.05],
    [8, 5, "ハチバン", 150.0, 0.02, 0.02, 0.30, 0.002, 0.30, 0.02, 0.02, 0.02],
]
RACE = ScheduledRace(rid="2026110547150401", venue="笠松", number=1, name="", post=datetime(2026, 11, 5, 10, 25))


def _forecast(timing: str) -> dict:
    return {"title": f"2026110547150401（2026-11-05）の予測: {timing}の時点", "columns": COLUMNS, "rows": [list(row) for row in ROWS], "note": "", "meta": {}}


def test_当日は見出し_印の付いた全頭の表_単勝と複勝の買い目() -> None:
    text = LocalRaceMessage().describe(_forecast("当日"), RACE)
    lines = text.splitlines()
    assert lines[0] == "**笠松 1R（10:25 発走）** 地方の予想・当日の時点"
    assert lines[1].startswith("印 馬番 馬名 |")
    assert lines[2] == "◎ 7 イチバン | 3.0 | 78% | 35% | 1.10 | 1.05"
    assert lines[3].startswith("○ 4 ニバン |")
    assert len(lines[2:10]) == 8
    assert "実際に買う:" in lines
    assert "単勝 ◎7 イチバン（期待値 1.05）100円" in lines
    assert "複勝 3 ヨンバン（期待値 1.30）100円" in lines


def test_前日の時点は買い目を出さず_その旨を書く() -> None:
    text = LocalRaceMessage().describe(_forecast("前日"), RACE)
    assert "前日の時点（馬体重が届く前なのでオッズだけ）" in text.splitlines()[0]
    assert "買い目: なし（馬体重が届く前の前日の時点では買わない）" in text
    assert "100円" not in text


def test_レース一覧に無ければ_predict_の見出しを使う() -> None:
    text = LocalRaceMessage().describe(_forecast("当日"), None)
    assert text.startswith("**2026110547150401（2026-11-05）の予測: 当日の時点** 地方の予想・当日の時点")
