"""血統ごとの産駒の成績（条件別と、全体との差）。合成DB だけを使う。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db, pedigree, perf
from 共通.filters import Filters
from 合成DB import synth


def _db_with_two_sires(path: Path) -> Path:
    """父Aの産駒は東京の芝で強く、父Bの産駒は中山の芝で強い合成DB。

    同じ馬番の馬が、レースごとに違う父を持つように血統を入れ替える。
    """
    rows = synth.Sample()
    for day, venue, track in (("20240406", "05", "11"), ("20240413", "05", "11"),
                              ("20240420", "06", "17"), ("20240427", "06", "17")):
        # 東京（05）は馬番4 が勝ち、中山（06）は馬番1 が勝つ
        rows.extend(synth.simple_race(day, "01", venue=venue, track=track, fav_fin=4 if venue == "05" else 1))
    # simple_race が付ける既定の血統（馬番1 が父A）を捨てて、ここで全頭に付け直す
    rows.pedigree.clear()
    for number in range(1, 7):
        hid = f"2020{number:06d}"
        sire = "父A" if number == 4 else "父B"
        rows.pedigree.extend(synth.pedigree(hid, sire=sire, grandsire=f"{sire}の父", damsire="母父X"))
    return synth.build_db(path, rows)


@pytest.fixture
def sire_db(tmp_path: Path) -> Path:
    return _db_with_two_sires(tmp_path / "sire.duckdb")


def test_catalog_lists_roles_and_splits():
    names = {row[1] for row in pedigree.catalog().rows}
    assert {"父", "父の父", "母父"} <= names and {"競馬場", "芝ダ", "馬場状態", "距離帯"} <= names


@pytest.mark.parametrize("name", ["父", "父の父", "母父"])
def test_role_is_a_known_dimension(name: str):
    assert pedigree.role(name).name in perf.DIMENSIONS


def test_unknown_role_and_split_are_reported():
    with pytest.raises(LookupError, match="血統の立場"):
        pedigree.role("祖母")
    with pytest.raises(LookupError, match="条件"):
        pedigree.split("天気")


def test_edges_compare_with_the_pedigree_and_with_the_other_horses(sire_db: Path):
    with db.open_db(sire_db) as con:
        rows = pedigree.split_rows(con, pedigree.role("父"), pedigree.split("競馬場"), Filters(),
                                   min_runs=1, min_split_runs=1)
    by_key = {(row.name, row.split_labels[0]): row for row in rows}
    # 父A の産駒（馬番4）は東京で1着、中山で着外
    tokyo, nakayama = by_key[("父A", "東京")], by_key[("父A", "中山")]
    assert tokyo.pedigree_edge > 0 > nakayama.pedigree_edge
    assert tokyo.pedigree_edge == pytest.approx(tokyo.rate - tokyo.overall.rates()["複勝率"])
    # 東京では、ほかの血統より強い
    assert tokyo.baseline_edge > 0 > nakayama.baseline_edge
    assert tokyo.baseline_edge == pytest.approx(tokyo.rate - tokyo.baseline.rates()["複勝率"])


def test_baseline_is_the_rate_of_all_horses_in_that_condition(sire_db: Path):
    with db.open_db(sire_db) as con:
        rows = pedigree.split_rows(con, pedigree.role("父"), pedigree.split("競馬場"), Filters(),
                                   min_runs=1, min_split_runs=1)
        all_horses = pedigree.baseline_rows(con, pedigree.split("競馬場"), Filters())
    for row in rows:
        assert row.baseline == all_horses[row.split_labels]


def test_name_narrows_to_one_pedigree(sire_db: Path):
    with db.open_db(sire_db) as con:
        rows = pedigree.split_rows(con, pedigree.role("父"), pedigree.split("競馬場"), Filters(),
                                   min_runs=1, min_split_runs=1, name="父A")
    assert {row.name for row in rows} == {"父A"}


def test_unknown_name_is_reported(sire_db: Path):
    with db.open_db(sire_db) as con:
        with pytest.raises(LookupError, match="産駒"):
            pedigree.split_rows(con, pedigree.role("父"), pedigree.split("競馬場"), Filters(),
                                min_runs=1, min_split_runs=1, name="居ない父")


def test_rare_pedigrees_are_dropped(sire_db: Path):
    with db.open_db(sire_db) as con:
        rows = pedigree.split_rows(con, pedigree.role("父"), pedigree.split("競馬場"), Filters(),
                                   min_runs=1000, min_split_runs=1)
    assert rows == []


def test_sorted_rows_ranks_by_the_chosen_key(sire_db: Path):
    with db.open_db(sire_db) as con:
        rows = pedigree.split_rows(con, pedigree.role("父"), pedigree.split("競馬場"), Filters(),
                                   min_runs=1, min_split_runs=1)
    for sort_key in pedigree.SORT_KEYS:
        top = pedigree.sorted_rows(rows, sort_key=sort_key, top=1)
        assert top[0].sort_value(sort_key) == max(row.sort_value(sort_key) for row in rows)


def test_unknown_sort_key_is_reported(sire_db: Path):
    with pytest.raises(ValueError, match="並べ方"):
        pedigree.sorted_rows([], sort_key="単勝回収率")


def test_table_has_perf_columns_and_the_edge(sire_db: Path):
    split_dim = pedigree.split("芝ダ")
    with db.open_db(sire_db) as con:
        rows = pedigree.split_rows(con, pedigree.role("父"), split_dim, Filters(), min_runs=1, min_split_runs=1)
        table = pedigree.split_table(rows, "父", split_dim, Filters())
    assert table.columns == ["父", "芝ダ", *perf.PERF_COLUMNS,
                             pedigree.PEDIGREE_EDGE_COLUMN, pedigree.BASELINE_EDGE_COLUMN]
    assert all(row[-1].startswith(("+", "-")) and row[-2].startswith(("+", "-")) for row in table.rows)


def test_overall_table_has_one_row_per_pedigree(sire_db: Path):
    with db.open_db(sire_db) as con:
        overall = pedigree.overall_rows(con, pedigree.role("父"), Filters(), min_runs=1)
        table = pedigree.overall_table(overall, "父", Filters())
    assert {row[0] for row in table.rows} == {"父A", "父B"}
