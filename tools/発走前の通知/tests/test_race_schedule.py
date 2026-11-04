"""RaceSchedule（その日のレース一覧）のテスト。レース一覧の行は架空。"""

from __future__ import annotations

from datetime import datetime

from 共通 import card

from 発走前の通知.race_schedule import RaceSchedule

_HEADERS = card.CARD_LIST_HEADERS


def _row(**values) -> list:
    row = [None] * len(_HEADERS)
    for name, value in values.items():
        row[_HEADERS.index(name)] = value
    return row


def test_障害と発走時刻の無いレースを除いて発走の早い順() -> None:
    rows = [
        _row(場="東京", R=2, 発走="10:30", レース名="", コース="ダート・左", rid="2025041905010102"),
        _row(場="東京", R=1, 発走="10:00", レース名="", コース="芝・左", rid="2025041905010101"),
        _row(場="東京", R=3, 発走="11:00", レース名="障害未勝利", コース="障害・芝", rid="2025041905010103"),
        _row(場="京都", R=1, 発走=None, レース名="", コース="芝・右", rid="2025041908010101"),
        _row(場="京都", R=11, 発走="15:35", レース名="テスト記念", コース="芝・右", rid="2025041908010111"),
    ]
    races = RaceSchedule.from_rows("2025-04-19", rows)
    assert [(race.venue, race.number) for race in races] == [("東京", 1), ("東京", 2), ("京都", 11)]
    assert races[0].post == datetime(2025, 4, 19, 10, 0)
    assert races[2].rid == "2025041908010111"
    assert races[2].name == "テスト記念"


def test_行が無ければ空() -> None:
    assert RaceSchedule.from_rows("2025-04-19", []) == []
