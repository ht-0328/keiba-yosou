"""事象の契約: 分母と分子の数え方、既定の規則、付随する列。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db, events
from 共通.filters import Filters, Range


def test_rule_from_defaults_and_overrides():
    lost = events.rule_from("lost")
    assert lost.pop == Range(1, 1) and lost.odds is None and lost.finish == Range(4, None)
    assert lost.describe() == "1番人気が4着以下（中止・失格を含む）"
    longshot = events.rule_from("longshot")
    assert longshot.pop is None and longshot.odds == Range(10, None) and longshot.describe() == "単勝10-倍が1着"
    assert events.rule_from("longshot", pop="8-").odds is None
    assert events.rule_from("longshot", pop="6-", odds="15-").describe() == "6-番人気 かつ 単勝15-倍が1着"
    assert events.rule_from("lost", finish="2-").finish == Range(2, None)
    with pytest.raises(ValueError):
        events.rule_from("draw")


def test_lost_favourites_counts_and_columns(synth_db: Path):
    """6レースの1番人気: 着順 4,1,2,4,1,3 → 4着以下は2頭。中止・取消は1番人気ではない。"""
    with db.open_db(synth_db) as con:
        table = events.search_events(con, events.rule_from("lost"), Filters())
        not_won = events.search_events(con, events.rule_from("lost", finish="2-"), Filters.from_mapping({"venue": "東京"}))
    assert table.meta == {**table.meta, "population": 6, "events": 2, "rate": round(2 / 6, 4)}
    assert "対象 6 頭のうち 2 頭（33.3%）" in table.note
    row = dict(zip(table.columns, table.rows[0]))
    assert row["人気"] == 1 and row["着順"] == 4 and row["勝ち馬"] == "ウマ04" and row["勝ち馬人気"] == 4 and row["勝ち馬単勝"] == 15.0
    assert row["1番人気"] == "ウマ01" and row["1番人気の着順"] == 4 and len(row["rid"]) == 16
    assert not_won.meta["population"] == 5 and not_won.meta["events"] == 4


def test_stopped_horse_counts_as_lost(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        table = events.search_events(con, events.rule_from("lost", pop="5"), Filters())
    assert table.meta["population"] == 1 and table.meta["events"] == 1 and table.rows[0][table.columns.index("異常")] == "競走中止"


def test_longshot_wins(synth_db: Path):
    with db.open_db(synth_db) as con:
        won = events.search_events(con, events.rule_from("longshot"), Filters())
        placed = events.search_events(con, events.rule_from("longshot", odds="10-", finish="1-4"), Filters())
        by_pop = events.search_events(con, events.rule_from("longshot", pop="4-"), Filters())
    assert won.meta["population"] == 12 and won.meta["events"] == 4  # 15倍と30倍（中止）が対象、15倍の4勝
    assert placed.meta["events"] == 6  # 15倍の馬は 1着4回・4着2回
    assert by_pop.meta["population"] == 12 and by_pop.meta["events"] == 4
    assert won.rows[0][won.columns.index("単勝払戻")] == 1500


def test_note_carries_subject_counts(synth_db: Path):
    with db.open_db(synth_db) as con:
        table = events.search_events(con, events.rule_from("lost"), Filters())
    assert "対象の成績: 出走 6 着別度数 2-1-1-2" in table.note and table.meta["summary"]["複勝率"] == "66.7%"
