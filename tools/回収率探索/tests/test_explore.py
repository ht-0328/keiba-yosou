"""回収率探索の契約: 閾値以上の行だけ、回収率の高い順、年ごとの回収率、組み合わせ。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db, explore, perf
from 共通.filters import Filters


def test_hits_are_above_threshold_and_sorted(synth_db: Path):
    with db.open_db(synth_db) as con:
        table = explore.explore(con, Filters.from_mapping({"venue": "東京"}), ["popularity", "frame"], min_runs=1)
    assert table.columns == list(explore.COLUMNS)
    rows = {(r[0], r[1]): r for r in table.rows}
    hit = rows[("単勝人気", "4")]  # 15倍の馬が5戦4勝
    assert hit[2] == "5" and hit[3] == "4-0-0-1" and hit[8] == "1200.0%" and hit[9] == "320.0%"
    assert hit[10].startswith("2024 ") and "2025 " in hit[10]
    assert rows[("枠番", "4")][8] == "1200.0%"
    assert ("単勝人気", "1") not in rows  # 40% / 66% は超えない
    scores = [max(float(r[8].rstrip("%")), float(r[9].rstrip("%"))) for r in table.rows]
    assert scores == sorted(scores, reverse=True)
    assert table.meta["hits"] == len(table.rows) and table.meta["baseline"]["着別度数"] == "5-5-5-10"
    assert "全体の成績" in table.note


def test_target_threshold_and_top(synth_db: Path):
    with db.open_db(synth_db) as con:
        place_only = explore.explore(con, Filters(), ["popularity"], min_runs=1, target="place", threshold=1.5)
        top1 = explore.explore(con, Filters(), ["popularity"], min_runs=1, top=1)
        with pytest.raises(ValueError):
            explore.explore(con, Filters(), ["popularity"], target="show")
        with pytest.raises(LookupError):
            explore.explore(con, Filters(), ["nope"])
    assert all(float(r[9].rstrip("%")) >= 150 for r in place_only.rows)
    assert len(top1.rows) == 1


def test_pairs_and_limit(synth_db: Path):
    with db.open_db(synth_db) as con:
        paired = explore.explore(con, Filters(), ["popularity", "condition"], min_runs=1, pairs=True)
        with pytest.raises(ValueError):
            explore.explore(con, Filters(), list(explore.DEFAULT_DIMENSIONS), pairs=True)
    assert any(r[0] == "単勝人気×芝ダート・馬場状態" for r in paired.rows)


def test_default_dimensions_exist_and_catalog_marks_them():
    dims = explore.dimensions_from(None)
    assert [d.name for d in dims] == list(explore.DEFAULT_DIMENSIONS)
    marked = {r[0] for r in explore.catalog().rows if r[2] == "○"}
    assert marked == set(explore.DEFAULT_DIMENSIONS)
    assert explore.passes(perf.PerfRow(("x",), 10, 1, 0, 0, 1000, 500), "win", 1.0)
    assert not explore.passes(perf.PerfRow(("x",), 10, 1, 0, 0, 999, 500), "win", 1.0)
