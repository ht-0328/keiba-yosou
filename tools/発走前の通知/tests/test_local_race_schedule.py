"""LocalRaceSchedule（地方のその日のレース一覧）のテスト。行は架空。"""

from __future__ import annotations

from datetime import datetime

from 発走前の通知.local_race_row import LocalRaceRow
from 発走前の通知.local_race_schedule import LocalRaceSchedule


def test_発走時刻のあるレースを早い順に_競馬場コードは名前にする() -> None:
    rows = [
        LocalRaceRow(rid="2026110550150402", venue_code="50", number=2, name="", post="1110"),
        LocalRaceRow(rid="2026110547150401", venue_code="47", number=1, name="", post="1025"),
        LocalRaceRow(rid="2026110530150411", venue_code="30", number=11, name="テスト特別", post="2000"),
        LocalRaceRow(rid="2026110543150401", venue_code="43", number=1, name="", post=""),
    ]
    races = LocalRaceSchedule.from_rows("2026-11-05", rows)
    assert [race.rid for race in races] == ["2026110547150401", "2026110550150402", "2026110530150411"]
    assert races[0].venue == "笠松"
    assert races[0].post == datetime(2026, 11, 5, 10, 25)
    assert races[2].label == "門別 11R テスト特別（20:00 発走）"
