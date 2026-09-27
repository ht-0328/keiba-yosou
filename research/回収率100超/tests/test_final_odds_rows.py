"""オッズを読むリポジトリが、確定オッズの断面だけを読むことのテスト。架空の値だけを使う。

オッズの表には、確定オッズのほかに締め切り前の断面（時系列オッズ・速報オッズ）が入りうる。
混ざると、断面をまたいで足し合わせた値になってしまう。
"""

from __future__ import annotations

import duckdb
import pytest

from 回収率100超.analysis.repository import (
    POOL_MARGINALS,
    PoolMarginalRepository,
    PoolSizeRepository,
    PositionMarginalRepository,
)

KEYS = ("開催年", "開催月日", "競馬場コード", "開催回[第N回]", "開催日目[N日目]", "レース番号")
RACE = ("2026", "0906", "06", "04", "02", "11")
RID = "".join(RACE)


def _create(con: duckdb.DuckDBPyConnection, table: str, columns: tuple[str, ...]) -> None:
    listed = ", ".join(f'"{column}" VARCHAR' for column in columns)
    con.execute(f'CREATE TABLE "{table}" ({listed})')


def _snapshot(con, announced: str, stage: str, odds: tuple[str, str]) -> None:
    """3連単の断面1つ（2通りの組だけ）と、その票数の合計。"""
    con.execute('INSERT INTO o6 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [*RACE, stage, announced, "1000"])
    for combo, value in zip(("010203", "020103"), odds, strict=True):
        con.execute('INSERT INTO "o6__3連単オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [*RACE, announced, combo, value])


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    _create(con, "o6", (*KEYS, "データ区分", "発表月日時分", "3連単票数合計"))
    _create(con, "o6__3連単オッズ", (*KEYS, "発表月日時分", "組番", "オッズ"))
    _snapshot(con, "09061000", "1", ("0010", "0090"))  # 締め切り前: 1番の勝率 0.9
    _snapshot(con, "00000000", "5", ("0030", "0030"))  # 確定: 1番の勝率 0.5
    return con


def test_券種プールの確率は確定の断面だけから作る(con) -> None:
    marginal = next(item for item in POOL_MARGINALS if item.key == "trifecta_win")
    frame = PoolMarginalRepository(con, 2026).read(marginal).set_index("horse_no")
    assert frame.loc[1, marginal.column] == pytest.approx(0.5)


def test_着順ごとの確率は確定の断面だけから作る(con) -> None:
    frame = PositionMarginalRepository(con, 2026).read("trifecta_positions").set_index("horse_no")
    assert frame.loc[1, "3連単の1着率"] == pytest.approx(0.5)
    assert frame.loc[1, "3連単の2着率"] == pytest.approx(0.5)


def test_プールの大きさは確定の断面の票数を読む(con) -> None:
    for table in ("o1", "o2", "o3", "o5"):
        column = {"o1": ("単勝票数合計", "複勝票数合計"), "o2": ("馬連票数合計",), "o3": ("ワイド票数合計",),
                  "o5": ("3連複票数合計",)}[table]
        _create(con, table, (*KEYS, "データ区分", "発表月日時分", *column))
    con.execute("INSERT INTO o1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [*RACE, "1", "09061000", "999999", "999999"])
    con.execute("INSERT INTO o1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [*RACE, "5", "00000000", "500", "300"])
    frame = PoolSizeRepository(con, 2026).read().set_index("rid")
    assert frame.loc[RID, "単勝プールの大きさ"] == 500 and frame.loc[RID, "3連単プールの大きさ"] == 1000
