"""OddsSnapshotRepository・WinPayoutRepository・TrifectaPayoutRepository のテスト。メモリ上の DuckDB に架空の行を入れる。"""

from __future__ import annotations

import duckdb
import pytest

from 地方の直前の買い目.repository import OddsSnapshotRepository, TrifectaPayoutRepository, WinPayoutRepository

RID = "2026111844120105"
_KEY = ("開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号")
_KEY_VALUES = ("2026", "1118", "44", "12", "01", "05")
_OTHER_RACE = ("2026", "1118", "44", "12", "01", "06")
_OTHER_DAY = ("2026", "1201", "44", "12", "01", "05")


def _create(con: duckdb.DuckDBPyConnection, table: str, columns: tuple[str, ...]) -> None:
    con.execute(f'CREATE TABLE "{table}" ({", ".join(f"{name} VARCHAR" for name in (*_KEY, *columns))})')


def _insert(con: duckdb.DuckDBPyConnection, table: str, rows: list[tuple], key: tuple[str, ...] = _KEY_VALUES) -> None:
    for row in rows:
        con.execute(f'INSERT INTO "{table}" VALUES ({", ".join("?" for _ in (*key, *row))})', [*key, *row])


def _odds_db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    _create(con, "o1", ("データ区分", "発表月日時分"))
    _create(con, "o1__単勝オッズ", ("発表月日時分", "馬番", "オッズ"))
    _create(con, "o1__複勝オッズ", ("発表月日時分", "馬番", "最低オッズ", "最高オッズ"))
    _insert(con, "o1", [("1", "11181500"), ("1", "11181510"), ("1", "11181521"), ("1", "11181530"), ("3", "11181541")])
    # 1番: 断面ごとに 3.0 → 2.8 → 2.5 → 2.4（確定 2.0）。2番: 最後の発売中の断面で取消（オッズ 0）。3番: 最初の断面にオッズが無い。
    wins = [("11181500", "01", "0030"), ("11181510", "01", "0028"), ("11181521", "01", "0025"), ("11181530", "01", "0024"), ("11181541", "01", "0020"),
            ("11181500", "02", "0100"), ("11181510", "02", "0110"), ("11181521", "02", "0120"), ("11181530", "02", "0000"),
            ("11181500", "03", "----"), ("11181521", "03", "0500"), ("11181530", "03", "0450"), ("11181530", "03", "0450")]
    _insert(con, "o1__単勝オッズ", wins)
    _insert(con, "o1__複勝オッズ", [("11181530", "01", "0011", "0014"), ("11181530", "03", "0080", "0120"), ("11181521", "01", "0012", "0015")])
    _insert(con, "o1", [("1", "11181530")], key=_OTHER_RACE)
    _insert(con, "o1__単勝オッズ", [("11181530", "01", "0990")], key=_OTHER_RACE)
    return con


def test_今_約10分前_約20分前_最初の断面の単勝と_今の複勝() -> None:
    frame = OddsSnapshotRepository(_odds_db()).load(RID).set_index("horse_no")
    assert frame.index.tolist() == [1, 3]                                   # 取消の 2番は今の断面に無いので外れる
    assert frame.loc[1, ["odds_now", "odds_a", "odds_b", "odds_first"]].tolist() == [2.4, 2.8, 2.8, 3.0]   # 20分前より前は 15:10 の断面
    assert frame.loc[1, ["place_low", "place_high"]].tolist() == [1.1, 1.4]
    assert frame.loc[3, "odds_now"] == 45.0 and frame.loc[3, "odds_first"] == 50.0
    assert frame.loc[3, "odds_a"] != frame.loc[3, "odds_a"]                  # 10分前より前の断面が無い（欠損）
    assert set(frame["announced"]) == {"11181530"}                          # 締め切り後の断面（確定）は使わない


def test_断面が無ければ空の表() -> None:
    assert OddsSnapshotRepository(_odds_db()).load("2026111844120112").empty


def test_単勝と3連単の払戻を_開催日の範囲で読む() -> None:
    con = duckdb.connect()
    _create(con, "hr__単勝払戻", ("馬番", "払戻金"))
    _create(con, "hr__3連単払戻", ("組番", "払戻金"))
    _insert(con, "hr__単勝払戻", [("06", "000001200"), ("  ", "000000000")])
    _insert(con, "hr__3連単払戻", [("060201", "000050000"), ("      ", "")])
    _insert(con, "hr__単勝払戻", [("01", "000000150")], key=_OTHER_DAY)
    wins = WinPayoutRepository(con).load("20261118", "20261118")
    assert wins.to_dict("records") == [{"race_id": RID, "horse_no": 6, "payout": 1200}]
    assert len(WinPayoutRepository(con).load("20261101", "20261231")) == 2
    trifectas = TrifectaPayoutRepository(con).load("20261118", "20261118")
    assert trifectas.to_dict("records") == [{"race_id": RID, "first": 6, "second": 2, "third": 1, "payout": 50000}]
    with pytest.raises(duckdb.Error):
        WinPayoutRepository(duckdb.connect()).load("20261118", "20261118")
