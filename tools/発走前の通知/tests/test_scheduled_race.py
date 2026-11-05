"""ScheduledRace（1レースの発走時刻）のテスト。値は架空。"""

from __future__ import annotations

from datetime import datetime

from 発走前の通知.scheduled_race import ScheduledRace


def test_何分前の時刻と開催日() -> None:
    race = ScheduledRace("2025041905010111", "東京", 11, "テスト記念", datetime(2025, 4, 19, 15, 45))
    assert race.due_at(10) == datetime(2025, 4, 19, 15, 35)
    assert race.day == "2025-04-19"


def test_短い名前はレース名が無ければ場とRだけ() -> None:
    named = ScheduledRace("2025041905010111", "東京", 11, "テスト記念", datetime(2025, 4, 19, 15, 45))
    plain = ScheduledRace("2025041905010101", "東京", 1, "", datetime(2025, 4, 19, 10, 0))
    assert named.label == "東京 11R テスト記念（15:45 発走）"
    assert plain.label == "東京 1R（10:00 発走）"
