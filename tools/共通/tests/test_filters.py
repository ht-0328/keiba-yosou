"""絞り込みの契約: 範囲の書き方、値の正規化、WHERE 句、読みやすい形。"""

from __future__ import annotations

import pytest

from 共通.filters import FILTER_FIELDS, Filters, Range, parse_date


@pytest.mark.parametrize("text,low,high", [("1600", 1600, 1600), ("1400-1800", 1400, 1800), ("1400-", 1400, None), ("-1800", None, 1800), ("1.5-2.9", 1.5, 2.9)])
def test_range_parse(text, low, high):
    r = Range.parse(text)
    assert (r.low, r.high) == (low, high)
    assert Range.parse(r.text()) == r


@pytest.mark.parametrize("bad", ["", "-", "abc", "1800-1400"])
def test_range_parse_rejects(bad):
    with pytest.raises(ValueError):
        Range.parse(bad)


def test_range_sql_and_contains():
    assert Range.parse("1-3").sql("p") == ("p BETWEEN ? AND ?", [1, 3])
    assert Range.parse("10-").sql("o") == ("o >= ?", [10])
    assert Range.parse("-8").contains(8) and not Range.parse("-8").contains(9) and not Range.parse("1").contains(None)


def test_parse_date_accepts_both_forms():
    assert parse_date("20240101") == "2024-01-01" and parse_date("2024-01-01") == "2024-01-01"
    with pytest.raises(ValueError):
        parse_date("2024/01/01")


def test_from_mapping_normalizes_and_ignores_unknown_or_empty():
    f = Filters.from_mapping({"venue": "東京", "course": "芝・左", "condition": "稍", "class": "G1", "pop": "1-3",
                              "from": "20240101", "sex": "セ", "surface": "ダ", "unknown": "x", "odds": "", "jockey": None})
    assert f.venue == "05" and f.course == ("11",) and f.condition == "2" and f.class_name == "G1"
    assert f.pop == Range(1, 3) and f.date_from == "2024-01-01" and f.sex == "セン" and f.surface == "ダート"
    assert f.odds is None and f.jockey is None
    with pytest.raises(ValueError):
        Filters.from_mapping({"venue": "大井"})


def test_where_uses_fact_columns_and_params():
    f = Filters.from_mapping({"venue": "05", "course": "芝・左", "distance": "1600", "condition": "良", "pop": "1", "jockey": "A", "to": "2026-09-06", "month": "6-8"})
    sql, params = f.where("f")
    assert "f.venue_code = ?" in sql and "f.track_code IN (?)" in sql and "f.distance_m BETWEEN ? AND ?" in sql
    assert "f.condition_code = ?" in sql and "contains(f.jockey, ?)" in sql and "f.race_date <= ?" in sql and "f.month BETWEEN ? AND ?" in sql
    assert params == ["05", "11", 1600, 1600, "1", 1, 1, "A", "2026-09-06", 6, 8]
    assert Filters().where() == ("TRUE", []) and Filters().is_empty()


def test_describe_and_cli_args():
    f = Filters.from_mapping({"venue": "東京", "course": "芝・左", "distance": "1600", "condition": "良", "pop": "1", "from": "2024-01-01"})
    assert f.describe() == "東京 芝・左 1600m 良 1番人気 2024-01-01〜"
    assert f.cli_args() == "--venue 05 --course 芝・左 --distance 1600 --condition 良 --pop 1 --from 2024-01-01"
    assert Filters().describe() == "全レース"


def test_every_field_has_unique_name():
    names = [f.name for f in FILTER_FIELDS]
    assert len(names) == len(set(names))
    Filters.from_mapping({f.name: f.example for f in FILTER_FIELDS})


def test_finish_filter_and_cli_exclude(synth_db):
    from 共通 import cli, db, runners
    f = Filters.from_mapping({"finish": "1-3"})
    sql, params = f.where()
    assert sql == "finish BETWEEN ? AND ?" and params == [1, 3] and f.describe() == "1-3着"
    with db.open_db(synth_db) as con:
        winners = runners.search_runners(con, Filters.from_mapping({"finish": "1"}))
        placed = runners.search_runners(con, Filters.from_mapping({"pop": "1", "finish": "4-"}))
    assert winners.meta["total"] == 6 and all(row[winners.columns.index("着順")] == 1 for row in winners.rows)
    assert placed.meta["total"] == 2  # 競走中止（着順なし）は含まない
    parser = cli.build_parser("t", filters=True, filter_help={"finish": "事象"})
    args = parser.parse_args(["--finish", "4-", "--venue", "東京"])
    assert cli.filters_from(args).finish == Range(4, None)
    assert cli.filters_from(args, exclude=("finish",)).finish is None and cli.filter_value(args, "finish") == "4-"
