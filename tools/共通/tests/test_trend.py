"""傾向スコアの契約: 判定の線引き、手入力の読み方、母集団は開催日より前だけ、当日の馬への当てはめ、登録簿と一覧の一致。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from 合成DB import synth
from 共通 import db, perf, race, trend, trend_items

#: 確定前の出馬表（2025-04-19 東京 2R「合成特別」）。馬番が決まっている。
CARD_DAY, CARD_VENUE, CARD_RACE = "2025-04-19", "東京", 2
#: 標本の小さい合成DB でも判定が付く線引き。
LOOSE = trend.Options(min_runs=3, min_z=0.0)
ITEMS_DOC = Path(__file__).resolve().parents[2] / "傾向スコア" / "score-items.md"


def _row(runs: int, first: int, second: int, third: int) -> perf.PerfRow:
    return perf.PerfRow(("値",), runs, first, second, third, 0, 0)


def _score(path: Path, options: trend.Options = LOOSE, **manual: str) -> trend.TrendReport:
    with db.open_db(path) as con:
        rid = race.resolve_rid(con, CARD_DAY, CARD_VENUE, CARD_RACE)
        return trend.score_race(con, rid, trend.ManualInputs.parse(**manual), options)


def _hits(report: trend.TrendReport, horse_no: int) -> set[str]:
    return {hit.item_id for horse in report.horses if horse.entry["horse_no"] == horse_no for hit in horse.hits}


# ------------------------------------------------------------------ 判定

def test_classify_head_partner_bad_and_neutral():
    base = _row(1000, 70, 70, 70)  # 勝率 7%、連対率 14%、複勝率 21%
    no_z = trend.Options(min_z=0.0)
    assert trend.classify(_row(100, 12, 5, 5), base, no_z) == trend.HEAD        # 勝率 12% は 7% の 1.3 倍以上
    assert trend.classify(_row(100, 8, 8, 14), base, no_z) == trend.PARTNER     # 勝率は届かないが複勝率 30%
    assert trend.classify(_row(100, 3, 4, 5), base, no_z) == trend.BAD          # 複勝率 12% は 21% の 0.7 倍以下
    assert trend.classify(_row(100, 7, 7, 7), base, no_z) == trend.NEUTRAL
    assert trend.classify(_row(0, 0, 0, 0), base, no_z) == trend.NEUTRAL


def test_classify_requires_a_difference_that_is_unlikely_by_chance():
    base = _row(1000, 70, 70, 70)
    lucky = _row(20, 2, 1, 2)  # 勝率 10% だが、20 走で 2 勝は偶然でも起きる
    assert trend.classify(lucky, base, trend.Options(min_z=0.0)) == trend.HEAD
    assert trend.classify(lucky, base, trend.Options(min_z=1.0)) == trend.NEUTRAL
    assert trend.z_score(0.10, 0.07, 20) == pytest.approx(0.526, abs=0.01) and trend.z_score(0.1, 0.0, 20) == 0.0


def test_manual_inputs_parse_and_reject_bad_text():
    inputs = trend.ManualInputs.parse(condition="稍重", popularity="3:1, 7:2", weights="3:480:+2,7:502")
    assert inputs.condition_code == "2" and inputs.popularity == {3: 1, 7: 2} and inputs.weights == {3: (480, 2), 7: (502, None)}
    assert inputs.popularity_text() == "3:1,7:2" and inputs.weights_text() == "3:480:+2,7:502" and inputs.condition_name() == "稍重"
    assert trend.ManualInputs.parse() == trend.ManualInputs()
    for bad in ({"popularity": "3"}, {"popularity": "a:1"}, {"weights": "3:abc"}, {"condition": "晴"}):
        with pytest.raises(ValueError):
            trend.ManualInputs.parse(**bad)
    with pytest.raises(ValueError):
        trend.Options(scope="nope")


# ------------------------------------------------------------------ 採点

def test_scores_entries_of_an_unconfirmed_race(trend_db: Path):
    report = _score(trend_db, condition="良")
    ranked = [horse.entry["horse_no"] for horse in report.horses]
    assert ranked[0] == 4 and ranked[-1] == 1 and not report.result_known()      # いつも勝つ馬番4 が1位、いつも4着の馬番1 が最下位
    winner, favourite = _hits(report, 4), _hits(report, 1)
    assert {"P03", "P07", "P19"} <= winner and not {hit for hit in winner if hit.startswith("M")}  # 馬番・推定脚質（逃げ）・同レース勝利
    assert {"M03", "M19"} <= favourite and "P20" in _hits(report, 2)             # 馬番2 は同レースで2着だけ
    assert "P19" not in _hits(report, 7) and "M19" not in _hits(report, 7)       # 初出走の馬番7 に同レースの実績は無い
    levels = {level["key"]: level for level in report.levels}
    assert levels["same"]["races"] == 2 and levels["match4"]["races"] == 6 and levels["match4"]["runs"] == 30
    assert perf.NEED_POPULARITY in report.missing and perf.NEED_WEIGHT in report.missing and perf.NEED_GOING not in report.missing


def test_without_condition_the_four_match_level_is_empty(trend_db: Path):
    report = _score(trend_db)
    levels = {level["key"]: level for level in report.levels}
    assert levels["match4"]["races"] == 0 and levels["match3"]["races"] == 6 and perf.NEED_GOING in report.missing
    assert "P27" not in _hits(report, 4)  # 持ち時計は馬場状態が要る
    assert report.horses[0].entry["horse_no"] == 4


def test_popularity_input_enables_the_favorite_items(trend_db: Path):
    """人気を入れると、人気馬の型（83〜95）が1〜3番人気の馬にだけ当てはまる。"""
    report = _score(trend_db, condition="良", popularity="1:1,4:6")

    def favorite_items(horse_no: int) -> set[str]:
        return {hit for hit in _hits(report, horse_no) if 83 <= int(hit[1:]) <= 95}

    assert perf.NEED_POPULARITY not in report.missing
    assert any(hit.startswith("M") for hit in favorite_items(1))   # 1番人気にした馬番1（いつも4着）は危険な人気馬の型
    assert favorite_items(4) == set() and favorite_items(2) == set()  # 6番人気の馬番4 と、人気を入れていない馬番2 は対象外
    with pytest.raises(ValueError):
        _score(trend_db, popularity="99:1")


def test_population_uses_only_races_before_the_race_day(trend_db: Path, tmp_path: Path):
    """同じ日と後の日のレースを足しても、母集団と点数が変わらない。"""
    before = _score(trend_db, condition="良")
    rows = synth.trend_sample()
    rows.extend(synth.simple_race("20250419", "05", fav_fin=1))   # 同じ日の別のレース（1番人気が勝つ）
    rows.extend(synth.simple_race("20250426", "01", fav_fin=1))   # 後の日
    after = _score(synth.build_db(tmp_path / "later.duckdb", rows), condition="良")
    assert [level["runs"] for level in before.levels] == [level["runs"] for level in after.levels]
    assert [(h.entry["horse_no"], h.score) for h in before.horses] == [(h.entry["horse_no"], h.score) for h in after.horses]


def test_confirmed_race_shows_finish_and_uses_earlier_races_only(trend_db: Path):
    with db.open_db(trend_db) as con:
        first = trend.score_race(con, race.resolve_rid(con, "2024-04-06", "東京", 1), options=LOOSE)
        last = trend.score_race(con, race.resolve_rid(con, "2024-05-11", "東京", 1), options=LOOSE)
        tables = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables() WHERE temporary").fetchall()}
    assert first.result_known() and all(level["runs"] == 0 for level in first.levels) and all(h.score == 0 for h in first.horses)
    assert {level["key"]: level["races"] for level in last.levels}["match4"] == 5 and last.horses[0].entry["finish"] == 1
    assert tables == {"facts"}  # 採点の一時表は残さない
    assert "着順" in last.ranking_table().columns and "着順" not in _score(trend_db).ranking_table().columns


def test_scope_fixes_the_level_and_default_rule_needs_runs(trend_db: Path):
    same = _score(trend_db, trend.Options(scope="same", min_runs=2, min_z=0.0), condition="良")
    assert {hit.level for horse in same.horses for hit in horse.hits if hit.level} == {"same"}
    strict = _score(trend_db, trend.Options(), condition="良")  # 既定は出走数 20 以上。合成DB の値は 6 走までなので判定が付かない
    assert all(hit.level is None for horse in strict.horses for hit in horse.hits)


def test_report_tables_and_dict_are_consistent(trend_db: Path):
    report = _score(trend_db, condition="良")
    summary, ranking, highlights, breakdown, same_race = report.tables()
    assert ranking.rows[0][2] == 4 and ranking.rows[0][6].startswith("+") and len(ranking.rows) == 6
    assert len(breakdown.rows) == sum(len(horse.hits) for horse in report.horses)
    assert any(row[1] == "馬番" and row[3] == "4" and row[4] == trend.HEAD for row in highlights.rows)
    assert len(same_race.rows) == 6 and same_race.rows[0][6] == 1  # 同レース2回 × 3着まで
    data = json.loads(json.dumps(report.to_dict(), ensure_ascii=False, default=str))
    assert data["horses"][0]["no"] == 4 and data["counts"] == {"plus": 89, "minus": 75} and len(data["trends"]) == len(trend_items.FACTORS)
    number = next(t for t in data["trends"] if t["key"] == "number@all")
    four = next(label for label in number["labels"] if label["label"] == "4")
    assert four["verdict"] == trend.HEAD and four["rows"]["match4"]["counts"] == "6-0-0-0" and len(four["horses"]) == 1


def test_unknown_race_is_reported(trend_db: Path):
    with db.open_db(trend_db) as con:
        with pytest.raises(LookupError):
            trend.score_race(con, "2030010105010101")


# ------------------------------------------------------------------ 登録簿

def test_registry_is_valid_and_matches_the_item_list_document():
    trend_items.validate()
    assert trend_items.item_count() == {trend_items.PLUS: 89, trend_items.MINUS: 75}
    registered = {f.item_id(sign) for f in trend_items.FACTORS for sign in f.signs()} | {item.id for item in trend_items.FIXED_ITEMS}
    documented = set(re.findall(r"^\| ([PM]\d{2}) \|", ITEMS_DOC.read_text(encoding="utf-8"), flags=re.MULTILINE))
    assert registered == documented
    assert len(trend.catalog_table().rows) == len(registered)


def test_registry_rejects_result_side_dimensions_and_duplicates():
    leak = trend_items.Factor(99, 1, "脚質（結果）", ("style",))
    with pytest.raises(ValueError):
        trend_items.validate((leak,), ())
    with pytest.raises(ValueError):
        trend_items.validate((trend_items.FACTORS[0], trend_items.FACTORS[0]), ())
