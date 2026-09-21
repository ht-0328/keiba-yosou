"""成績7つの契約: 手計算と一致、切り口の帯、順位付け、組み合わせ。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db, perf
from 共通.filters import Filters


def test_popularity_perf_matches_hand_count(synth_db: Path):
    """東京の5レースの1番人気: 着順 4,1,2,4,3 → 1-1-1-2、払戻は勝った1回の 200 円と複勝3回の 110 円。"""
    with db.open_db(synth_db) as con:
        rows = perf.perf_rows(con, perf.dimension("popularity"), Filters.from_mapping({"venue": "東京"}))
        cover = perf.coverage(con, Filters.from_mapping({"venue": "東京"}))
    favourite = perf.find_row(rows, 1)
    assert favourite.runs == 5 and favourite.counts() == "1-1-1-2"
    assert favourite.cells() == ["5", "1-1-1-2", "20.0%", "40.0%", "60.0%", "40.0%", "40.0%", "66.0%"]
    assert perf.find_row(rows, 5).counts() == "0-0-0-5"  # 競走中止は出走して馬券外
    assert perf.find_row(rows, 6) is None  # 出走取消は数えない
    assert cover.races == 5 and cover.runs == 25 and cover.first_date == "2024-04-06"


def test_table_has_dimension_columns_and_perf_columns(synth_db: Path):
    with db.open_db(synth_db) as con:
        dim = perf.dimension("course")
        rows = perf.perf_rows(con, dim, Filters.from_mapping({"pop": "1"}))
        table = perf.perf_table(rows, dim, Filters.from_mapping({"pop": "1"}))
    assert table.columns == ["競馬場", "コース", "距離", "馬場状態", *perf.PERF_COLUMNS]
    assert [row[:4] for row in table.rows] == [["東京", "芝・左", 1600, "良"], ["東京", "ダート・左", 1600, "良"], ["中山", "芝・右", 1600, "稍重"]]


def test_ranked_dimension_sorts_and_limits(synth_db: Path):
    with db.open_db(synth_db) as con:
        rows = perf.perf_rows(con, perf.dimension("jockey"), top=2, min_runs=1)
        by_runs = perf.perf_rows(con, perf.dimension("jockey"), rank_by="出走数", min_runs=1)
        with pytest.raises(ValueError):
            perf.perf_rows(con, perf.dimension("jockey"), rank_by="人気")
    assert [row.labels[0] for row in rows] == ["騎手D", "騎手A"]  # 勝率順（穴の騎手D 6戦4勝、騎手A 12戦2勝）
    assert by_runs[0].labels[0] == "騎手A" and by_runs[0].runs == 12  # 馬番1と馬番5（競走中止）の両方に乗る


def test_band_labels_and_order():
    band = perf.Band("x", (2, 3), ("1位", "2位", "3位以下"))
    assert "WHEN x < 2 THEN '1位'" in band.label_sql() and "ELSE '3位以下'" in band.label_sql()
    assert band.order_sql().endswith("ELSE 2 END")
    with pytest.raises(ValueError):
        perf.Band("x", (2,), ("a",))


def test_cross_and_by_popularity_and_catalog(synth_db: Path):
    crossed = perf.cross(perf.dimension("class"), perf.dimension("popularity-top"))
    assert crossed.column_names == ("クラス", "人気帯") and "popularity IS NOT NULL" in crossed.where_sql
    with pytest.raises(ValueError):
        perf.cross(perf.dimension("popularity"), perf.dimension("popularity"))  # 同じ見出しが重なる
    with pytest.raises(LookupError):
        perf.dimension("nope")
    with db.open_db(synth_db) as con:
        rows = perf.perf_rows(con, perf.by_popularity(perf.dimension("condition")))
    assert rows[0].labels == ("芝", "良", 1)
    assert len(perf.catalog().rows) == len(perf.DIMENSIONS)


def test_summary_row_and_text(synth_db: Path):
    with db.open_db(synth_db) as con:
        row = perf.summary_row(con, Filters.from_mapping({"venue": "東京", "pop": "1"}))
        none = perf.summary_row(con, Filters.from_mapping({"venue": "小倉"}))
    assert row.counts() == "1-1-1-2" and perf.summary_text(row).startswith("出走 5 着別度数 1-1-1-2 / 勝率 20.0%")
    assert perf.summary_text(none) == "該当なし" and perf.summary_dict(none)["勝率"] == "—"


def test_trend_dimensions_label_frames_styles_and_experience(synth_db: Path):
    """枠帯・偶数奇数・最内大外・推定脚質・前後・同コースの実績の値の付き方。"""
    tokyo_turf = Filters.from_mapping({"venue": "東京", "surface": "芝"})
    with db.open_db(synth_db) as con:
        def labels(name: str) -> dict:
            return {row.labels[0]: row.runs for row in perf.perf_rows(con, perf.dimension(name), tokyo_turf)}
        assert labels("frame-band") == {"内枠": 8, "中枠": 12}           # 馬番 1・2 が内枠、3〜5 が中枠（4レース）
        assert labels("number-parity") == {"偶数": 8, "奇数": 12}
        assert labels("gate-edge") == {"最内": 4, "その他": 16}           # 大外の馬番6 は出走取消で数えない
        assert labels("style-before")["不明"] == 5 and labels("style-before")["逃げ"] == 3 and labels("style-side")["前"] == 15
        assert labels("course-place") == {"勝利あり": 5, "3着内あり": 6, "着外のみ": 4, "出走なし": 5}
        crossed = perf.cross(perf.dimension("frame-band"), perf.dimension("style-side"))
        assert ("内枠", "前") in {row.labels for row in perf.perf_rows(con, crossed, tokyo_turf)}
    assert crossed.needs == {perf.NEED_GATE} and perf.dimension("style").needs == {perf.NEED_RESULT}
    assert perf.dimension("best-time-rank").needs == {perf.NEED_GOING} and perf.dimension("jockey").needs == frozenset()
