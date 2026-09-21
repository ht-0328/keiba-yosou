"""出走の検索の契約: 絞り込み・並べ替え・件数・上限。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db, runners
from 共通.filters import Filters


def test_search_filters_sorts_and_counts(synth_db: Path):
    with db.open_db(synth_db) as con:
        table = runners.search_runners(con, Filters.from_mapping({"venue": "東京", "pop": "1"}))
        by_odds = runners.search_runners(con, Filters.from_mapping({"venue": "東京", "surface": "芝"}), sort="odds", limit=2)
        paged = runners.search_runners(con, Filters(), limit=10, offset=25)
    assert table.meta["total"] == 5 and len(table.rows) == 5
    assert table.columns[:3] == ["日付", "場", "R"] and table.rows[0][0] == "2025-04-12"
    assert "全 5 件のうち 1〜5 件" in table.note and "東京 1番人気" in table.title
    assert [row[table.columns.index("単勝")] for row in by_odds.rows] == [30.0, 30.0]  # 競走中止（出走扱い）の 30 倍が先
    assert paged.meta["total"] == 30 and len(paged.rows) == 5


def test_cancelled_horses_are_not_listed(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        table = runners.search_runners(con, Filters())
    assert table.meta["total"] == 5 and all(row[table.columns.index("馬番")] != 6 for row in table.rows)
    assert any(row[table.columns.index("異常")] == "競走中止" for row in table.rows)


def test_unknown_sort_is_rejected(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        with pytest.raises(ValueError):
            runners.search_runners(con, Filters(), sort="random")


def test_note_carries_counts_and_rates(synth_db: Path):
    with db.open_db(synth_db) as con:
        table = runners.search_runners(con, Filters.from_mapping({"venue": "東京", "pop": "1"}))
        empty = runners.search_runners(con, Filters.from_mapping({"venue": "小倉"}))
    assert "着別度数 1-1-1-2 / 勝率 20.0% 連対率 40.0% 複勝率 60.0% 馬券外率 40.0% 単勝回収率 40.0% 複勝回収率 66.0%" in table.note
    assert table.meta["summary"]["着別度数"] == "1-1-1-2" and table.meta["summary"]["出走数"] == "5"
    assert "該当なし" in empty.note and empty.meta["summary"]["着別度数"] == "0-0-0-0"
