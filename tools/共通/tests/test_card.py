"""出馬表の契約: 確定前のレースが見られる、枠番・馬番が未定でも並ぶ、近走に当日の結果を混ぜない。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import card, db

#: 合成DB の確定前のレース（2025-04-19 東京）。1R は出走馬名表、2R は出馬表。
NAME_LIST_RID = "2025041905010101"
NUMBERED_RID = "2025041905010102"
#: 合成DB の確定済みのレース（2025-04-12 東京 1R）と、同じ日に2レースある日の 2R（2024-04-06 東京）。
FINAL_RID = "2025041205010101"
SECOND_RACE_OF_DAY_RID = "2024040605010102"


def records(table) -> list[dict]:
    return [dict(zip(table.columns, row)) for row in table.rows]


def test_list_cards_shows_races_on_and_after_the_start_date(card_db: Path):
    with db.open_db(card_db) as con:
        upcoming = card.list_cards(con, date_from="2025-04-19")
        nothing_yet = card.list_cards(con, date_from="20250420")
        with_past = card.list_cards(con, date_from="2025-04-12", date_to="2025-04-19", venue="東京")
        other_venue = card.list_cards(con, date_from="2025-04-19", venue="中山")
    assert upcoming.columns == list(card.CARD_LIST_HEADERS)
    rows = records(upcoming)
    assert [(r["日付"], r["曜"], r["場"], r["R"], r["状態"]) for r in rows] == [
        ("2025-04-19", "土", "東京", 1, "出走馬名表"), ("2025-04-19", "土", "東京", 2, "出馬表")]
    assert rows[0]["頭数"] == 6 and rows[0]["発走"] == "15:00" and rows[1]["レース名"] == "合成特別"  # 出走頭数が未定なら登録頭数
    assert [r["rid"] for r in rows] == [NAME_LIST_RID, NUMBERED_RID] and upcoming.meta["days"] == ["2025-04-19"]
    assert nothing_yet.rows == [] and nothing_yet.meta["total"] == 0 and "まだありません" in nothing_yet.note
    assert [r["状態"] for r in records(with_past)] == ["成績（確定）", "出走馬名表", "出馬表"]  # 発走の早い順
    assert other_venue.rows == []


def test_list_cards_rejects_unknown_venue_and_cuts_at_limit(card_db: Path):
    with db.open_db(card_db) as con:
        with pytest.raises(ValueError):
            card.list_cards(con, date_from="2025-04-19", venue="大井")
        cut = card.list_cards(con, date_from="2024-01-01", limit=3)
    assert len(cut.rows) == 3 and cut.meta["total"] == 8 and "打ち切り" in cut.note


def test_name_list_card_has_no_numbers_and_is_sorted_by_name(card_db: Path):
    with db.open_db(card_db) as con:
        detail = card.race_card(con, NAME_LIST_RID)
    header = detail.header
    assert header["状態"] == "出走馬名表" and header["頭数"] == 6 and header["馬場"] == "未発表" and header["天候"] == "未発表"
    assert header["重量"] == "馬齢" and detail.title().startswith("2025-04-19（土） 東京 1R")
    entries = records(detail.entries)
    assert detail.entries.columns == list(card.ENTRY_HEADERS)
    assert [e["馬名"] for e in entries] == ["ウマ01", "ウマ02", "ウマ03", "ウマ04", "ウマ05", "ウマ07"]
    assert all(e["枠"] is None and e["馬番"] is None and e["馬体重"] == "" and e["単勝"] is None for e in entries)
    assert all(e["タイム型"] is None and e["対戦型"] is None for e in entries)
    assert [t.title for t in detail.tables()][1:] == ["出馬表", "各馬の近走"]


def test_form_comes_from_runs_before_the_race_day(card_db: Path):
    with db.open_db(card_db) as con:
        entries = {e["馬名"]: e for e in records(card.race_card(con, NAME_LIST_RID).entries)}
    favourite = entries["ウマ01"]
    assert favourite["間隔(日)"] == 7 and favourite["近走着順"] == "4-1-2-3-1" and favourite["通算"] == "2-1-1-2"
    assert entries["ウマ05"]["近走着順"].startswith("中止-中止") and entries["ウマ05"]["通算"] == "0-0-0-6"
    first_timer = entries["ウマ07"]
    assert first_timer["間隔(日)"] is None and first_timer["近走着順"] == "" and first_timer["通算"] == ""


def test_form_never_includes_the_result_of_the_race_day(card_db: Path):
    with db.open_db(card_db) as con:
        final = card.race_card(con, FINAL_RID)
        second_of_day = card.race_card(con, SECOND_RACE_OF_DAY_RID)
    favourite = records(final.entries)[0]
    # 2025-04-12 の 4着は入らない。前走は 2024-04-07
    assert favourite["近走着順"] == "1-2-3-1-4" and favourite["間隔(日)"] == 370 and favourite["通算"] == "2-1-1-1"
    assert all(run["日付"] < "2025-04-12" for run in records(final.recent))
    assert not {"着順", "タイム", "着差"} & set(final.entries.columns)  # 今回の結果の列は持たない
    # 同じ日の 1R の結果も入らない（開催日より前だけ）
    assert all(e["近走着順"] == "" and e["通算"] == "" for e in records(second_of_day.entries))
    assert second_of_day.recent.rows == []


def test_numbered_card_has_frame_numbers_and_mining_ranks(card_db: Path):
    with db.open_db(card_db) as con:
        entries = records(card.race_card(con, NUMBERED_RID).entries)
    assert [(e["枠"], e["馬番"]) for e in entries] == [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (7, 7)]
    assert [e["対戦型"] for e in entries] == [1, 2, 3, 4, 5, 6]  # スコアの高い順
    assert [e["タイム型"] for e in entries] == [6, 5, 4, 3, 2, 1]  # 予想走破タイムの速い順
    assert entries[0]["騎手"] == "騎手1" and entries[0]["性齢"] == "牡4" and entries[0]["斤量"] == 57.0 and entries[0]["所属"] == "美浦"


def test_runs_limits_the_recent_table_but_not_the_form(card_db: Path):
    with db.open_db(card_db) as con:
        two = card.race_card(con, NUMBERED_RID, runs=2)
        none = card.race_card(con, NUMBERED_RID, runs=0)
    recent = records(two.recent)
    assert [(r["馬番"], r["走前"]) for r in recent][:4] == [(1, 1), (1, 2), (2, 1), (2, 2)]
    assert recent[0]["日付"] == "2025-04-12" and recent[0]["着順"] == 4 and len(recent[0]["rid"]) == 16
    assert max(r["走前"] for r in recent) == 2 and not any(r["馬番"] == 7 for r in recent)
    assert none.recent.rows == [] and records(none.entries)[0]["近走着順"] == "4-1-2-3-1"


def test_same_day_races_and_unknown_rid(card_db: Path):
    with db.open_db(card_db) as con:
        assert card.same_day_races(con, NUMBERED_RID) == [(1, NAME_LIST_RID), (2, NUMBERED_RID)]
        with pytest.raises(LookupError):
            card.race_card(con, "2025041905010112")
        with pytest.raises(ValueError):
            card.race_card(con, "123")
