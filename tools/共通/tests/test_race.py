"""レースの一覧と詳細の契約。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db, race
from 共通.filters import Filters


def test_list_races_groups_by_race_and_uses_runner_conditions(synth_db: Path):
    with db.open_db(synth_db) as con:
        all_races = race.list_races(con, Filters())
        tokyo_turf = race.list_races(con, Filters.from_mapping({"venue": "東京", "surface": "芝"}))
        with_jockey = race.list_races(con, Filters.from_mapping({"jockey": "騎手D", "pop": "4"}), limit=2)
    assert all_races.meta["total"] == 6 and len(all_races.rows) == 6 and all_races.rows[0][0] == "2025-04-12"
    assert tokyo_turf.meta["total"] == 4 and all(row[1] == "東京" for row in tokyo_turf.rows)
    assert with_jockey.meta["total"] == 6 and len(with_jockey.rows) == 2
    assert all_races.columns[-1] == "rid" and len(all_races.rows[0][-1]) == 16


def test_resolve_rid_and_detail(synth_db: Path):
    with db.open_db(synth_db) as con:
        rid = race.resolve_rid(con, "20240407", "中山", 3)
        detail = race.race_detail(con, rid)
        with pytest.raises(LookupError):
            race.resolve_rid(con, "2024-04-07", "東京", 12)
        with pytest.raises(LookupError):
            race.race_detail(con, "2024040705010112")
    assert rid == "2024040706010103"
    assert detail.header["競馬場"] == "中山" and detail.header["コース"] == "芝・右" and detail.header["馬場"] == "稍重"
    assert detail.header["クラス"] == "1勝クラス" and detail.header["頭数"] == 5 and detail.header["発走"] == "15:00"
    assert detail.title().startswith("2024-04-07 中山 3R")
    runners = detail.runners
    assert runners.columns == list(race.RUNNER_HEADERS) and [row[1] for row in runners.rows] == [1, 2, 3, 4, 5, 6]
    favourite = runners.rows[0]
    assert favourite[3] == "牡4" and favourite[4] == 57.0 and favourite[7] == "480(+2)" and favourite[8] == 1 and favourite[9] == 2.0
    assert favourite[10] == 1 and favourite[12] == "1:34.0" and favourite[13] == "+0.0" and favourite[14] == "1-1-1-1"
    cancelled = runners.rows[5]
    assert cancelled[11] == "出走取消" and cancelled[10] is None and cancelled[9] is None
    assert detail.payouts.rows[0] == ["単勝", "01", 200, 1] and len(detail.payouts.rows) == 4
    assert detail.corners.rows == [["4", "1", "1,2,3,4,5"]]
    assert detail.laps.rows == [] and "前3F 35" in detail.laps.note
    assert [t.title for t in detail.tables()][1:] == ["出走表・結果", "ラップ（200mごとの秒）", "通過順", "払戻"]
