"""最新の発表のオッズを読むリポジトリ（券種・3連単）のテスト。メモリ上の DuckDB に架空の発表を2つ入れ、新しいほうだけ読むことを見る。"""

from __future__ import annotations

import duckdb

from 地方の推奨買目.repository import AnnouncedTicketOddsRepository, AnnouncedTrifectaOddsRepository

RID = "2026110550170505"
_KEY = ("開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号")
_KEY_VALUES = ("2026", "1105", "50", "17", "05", "05")


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    key_sql = ", ".join(f"{name} VARCHAR" for name in _KEY)
    for head in ("o1", "o6"):
        con.execute(f"CREATE TABLE {head} (データ区分 VARCHAR, {key_sql}, 発表月日時分 VARCHAR)")
        con.executemany(f"INSERT INTO {head} VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [("1", *_KEY_VALUES, "11050933"), ("1", *_KEY_VALUES, "11051225")])
    con.execute(f'CREATE TABLE "o1__単勝オッズ" ({key_sql}, 発表月日時分 VARCHAR, 馬番 VARCHAR, オッズ VARCHAR)')
    con.executemany('INSERT INTO "o1__単勝オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [
        (*_KEY_VALUES, "11050933", "01", "0050"), (*_KEY_VALUES, "11051225", "01", "0045"), (*_KEY_VALUES, "11051225", "02", "0230"),
        (*_KEY_VALUES, "11051225", "03", "0000"),   # 発売の無い組
    ])
    con.execute(f'CREATE TABLE "o1__複勝オッズ" ({key_sql}, 発表月日時分 VARCHAR, 馬番 VARCHAR, 最低オッズ VARCHAR, 最高オッズ VARCHAR)')
    con.execute('INSERT INTO "o1__複勝オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (*_KEY_VALUES, "11051225", "01", "0012", "0018"))
    con.execute(f'CREATE TABLE "o6__3連単オッズ" ({key_sql}, 発表月日時分 VARCHAR, 組番 VARCHAR, オッズ VARCHAR)')
    con.executemany('INSERT INTO "o6__3連単オッズ" VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [
        (*_KEY_VALUES, "11050933", "010203", "0100"), (*_KEY_VALUES, "11051225", "010203", "0123"), (*_KEY_VALUES, "11051225", "020103", "0456"),
    ])
    return con


def test_券種のオッズは_最新の発表だけ_発売の無い組は出ない():
    con = _db()
    win = AnnouncedTicketOddsRepository(con, "単勝").load(RID).sort_values("a")
    assert list(win["a"]) == [1, 2] and list(win["odds"]) == [4.5, 23.0] and set(win["race_id"]) == {int(RID)}
    place = AnnouncedTicketOddsRepository(con, "複勝").load(RID)
    assert list(place["odds_lo"]) == [1.2] and list(place["odds_hi"]) == [1.8]
    assert AnnouncedTicketOddsRepository(con, "単勝").load("2026110550170506").empty


def test_3連単のオッズは_最新の発表の全部の組():
    trifecta = AnnouncedTrifectaOddsRepository(_db()).load(RID).sort_values(["first", "second"])
    assert [tuple(row) for row in trifecta[["first", "second", "third", "odds"]].itertuples(index=False)] == [(1, 2, 3, 12.3), (2, 1, 3, 45.6)]
