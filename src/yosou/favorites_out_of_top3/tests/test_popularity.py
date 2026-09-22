"""予測のときに使う人気の決め方（設計書 06 の図2・07 の「予測のときの人気の与え方」）。

実DB は使わない。締め切り前のオッズの SQL は、その表だけを入れた小さな DuckDB で確かめる。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from 共通 import db, keys

from yosou.shared.repository import AnnouncedOddsRepository
from yosou.shared.tests import synthetic_season as season

from ..dataset import PopularityApplier, PopularityInput

RACE = season.CARD_RACE_ID
#: 確定前の断面（データ区分 2）の発表時刻と、そのあとの確定の断面（データ区分 4）。
_BEFORE, _LATER, _FINAL = "01111000", "01111400", "01111600"


class _FixedOdds:
    """``AnnouncedOddsRepository`` の代わり（渡した表をそのまま返す）。"""

    def __init__(self, odds: pd.DataFrame) -> None:
        self._odds = odds

    def read(self, race_id: str) -> pd.DataFrame:
        return self._odds


def _odds_table(rows: list[tuple[int, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["horse_no", "odds"])


def test_popularity_input_reads_pairs_written_as_separate_arguments():
    assert PopularityInput.of(["3:1", "7:2", "11:3"]).as_mapping() == {3: 1, 7: 2, 11: 3}


def test_popularity_input_reads_pairs_written_with_commas():
    assert PopularityInput.of(["3:1,7:2"]).as_mapping() == {3: 1, 7: 2}
    assert PopularityInput.of(["3:1", "7:2,11:3"]).as_mapping() == {3: 1, 7: 2, 11: 3}


@pytest.mark.parametrize(("texts", "message"), [
    (["3-1"], "馬番:人気"),
    (["3:1:2"], "馬番:人気"),
    (["0:1"], "馬番"),
    (["3:0"], "人気"),
    (["a:1"], "馬番"),
    (["3:b"], "人気"),
    ([], "1つ以上"),
    (["3:1", "3:2"], "同じ馬番 3"),
    (["3:1", "7:1"], "同じ人気 1"),
])
def test_popularity_input_reports_what_is_wrong(texts: list[str], message: str):
    with pytest.raises(ValueError, match=message):
        PopularityInput.of(texts)


def test_given_popularity_comes_first():
    applier = PopularityApplier(_FixedOdds(_odds_table([(1, 2.0), (2, 3.0)])))
    given = PopularityInput.of(["5:1", "8:2"])
    assert applier.resolve(RACE, given) == {5: 1, 8: 2}


def test_odds_become_popularity_in_ascending_order():
    applier = PopularityApplier(_FixedOdds(_odds_table([(1, 8.4), (2, 2.1), (3, 5.0)])))
    assert applier.resolve(RACE, None) == {2: 1, 3: 2, 1: 3}


def test_no_popularity_is_left_to_the_database():
    # 渡された人気も締め切り前のオッズも無ければ None。元DB の単勝人気（確定単勝人気）がそのまま使われる
    applier = PopularityApplier(_FixedOdds(_odds_table([])))
    assert applier.resolve(RACE, None) is None


def _odds_db(path: Path, rows: list[tuple[str, str, int, str]]) -> duckdb.DuckDBPyConnection:
    """o1（親）と o1__単勝オッズ（子）だけを入れた小さな DB。``rows`` は（データ区分, 発表月日時分, 馬番, オッズ）。"""
    key_values = keys.split_rid(RACE)
    key_columns = ", ".join(f"{keys.q(name)} VARCHAR" for name in keys.RACE_KEY)
    key_literals = ", ".join(f"'{key_values[name]}'" for name in keys.RACE_KEY)
    con = duckdb.connect(str(path))
    con.execute(f'CREATE TABLE o1 ({key_columns}, "データ区分" VARCHAR, "発表月日時分" VARCHAR)')
    con.execute(f'CREATE TABLE "o1__単勝オッズ" ({key_columns}, "発表月日時分" VARCHAR,'
                ' "馬番" VARCHAR, "オッズ" VARCHAR)')
    for stage, announced_at, horse_no, odds in rows:
        con.execute(f"INSERT INTO o1 VALUES ({key_literals}, ?, ?)", [stage, announced_at])
        con.execute(f'INSERT INTO "o1__単勝オッズ" VALUES ({key_literals}, ?, ?, ?)',
                    [announced_at, f"{horse_no:02d}", odds])
    return con


def test_announced_odds_read_the_newest_snapshot_before_the_final_one(tmp_path: Path):
    rows = [
        ("2", _BEFORE, 1, "0021"), ("2", _BEFORE, 2, "0035"),
        ("2", _LATER, 1, "0048"), ("2", _LATER, 2, "0019"), ("2", _LATER, 3, "0000"),
        ("4", _FINAL, 1, "0012"),  # 確定後の断面は読まない
    ]
    with _odds_db(tmp_path / "odds.duckdb", rows) as con:
        odds = AnnouncedOddsRepository(con).read(RACE)
    # いちばん新しい確定前の断面だけ。オッズ 0000（発売なし）の馬は入れない
    assert odds["horse_no"].tolist() == [1, 2]
    assert odds["odds"].tolist() == [4.8, 1.9]


def test_announced_odds_are_empty_without_a_snapshot_before_the_final_one(tmp_path: Path):
    with _odds_db(tmp_path / "final-only.duckdb", [("4", _FINAL, 1, "0012")]) as con:
        assert AnnouncedOddsRepository(con).read(RACE).empty


def test_announced_odds_are_empty_when_the_database_has_no_odds_table(season_db: Path):
    # 今の元DB と同じく、合成DB には時系列オッズの表が無い
    with db.open_db(season_db) as con:
        odds = AnnouncedOddsRepository(con).read(RACE)
    assert odds.empty and list(odds.columns) == ["horse_no", "odds"]
