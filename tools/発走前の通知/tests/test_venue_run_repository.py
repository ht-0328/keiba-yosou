"""VenueRunRepository（1つの競馬場の期間内の出走）のテスト。メモリ上の DuckDB に架空の se と ra を入れる。"""

from __future__ import annotations

from datetime import date

import duckdb

from 発走前の通知.venue_run_repository import VenueRunRepository

_KEYS = ("開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号")
_SE = ("データ区分", "データ作成年月日", *_KEYS, "馬番", "確定着順",
       '"1コーナーでの順位"', '"2コーナーでの順位"', '"3コーナーでの順位"', '"4コーナーでの順位"')
_RA = ("データ区分", "データ作成年月日", *_KEYS, "トラックコード")


def make_tables(con: duckdb.DuckDBPyConnection, races: list[tuple[str, str, int, str, list[tuple[int, str, str]]]]) -> None:
    """``races`` は（競馬場コード, 開催日 'YYYYMMDD', レース番号, トラックコード, [(馬番, 確定着順, 4コーナーの順位), …]）。"""
    con.execute(f"CREATE TABLE se ({', '.join(f'{name} VARCHAR' for name in _SE)})")
    con.execute(f"CREATE TABLE ra ({', '.join(f'{name} VARCHAR' for name in _RA)})")
    for venue, day, race_no, track, horses in races:
        keys = (day[:4], day[4:], venue, "05", "02", f"{race_no:02d}")
        con.execute(f"INSERT INTO ra VALUES ({', '.join('?' for _ in _RA)})", ["7", day, *keys, track])
        for horse_no, finish, corner4 in horses:
            con.execute(f"INSERT INTO se VALUES ({', '.join('?' for _ in _SE)})",
                        ["7", day, *keys, f"{horse_no:02d}", finish, "00", "00", "00", corner4])


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    make_tables(con, [
        ("08", "20261108", 1, "17", [(1, "01", "02"), (2, "02", "00")]),   # 芝。2番は4コーナーの順位が無い
        ("08", "20261108", 2, "24", [(1, "00", "00")]),                    # ダート。まだ終わっていない
        ("08", "20261107", 1, "17", [(1, "01", "01")]),                    # 前の日
        ("05", "20261108", 1, "17", [(1, "01", "01")]),                    # ほかの競馬場
    ])
    con.execute(f"INSERT INTO se VALUES ({', '.join('?' for _ in _SE)})",  # 同じ馬の古い行（読まない）
                ["6", "20261107", "2026", "1108", "08", "05", "02", "01", "01", "03", "00", "00", "00", "09"])
    return con


def test_その競馬場の期間内の出走を_新しい行だけ_芝ダと着順と位置つきで読む() -> None:
    runs = VenueRunRepository(_db()).read("08", date(2026, 11, 8), date(2026, 11, 8))
    assert list(runs["race_id"]) == ["2026110808050201", "2026110808050201", "2026110808050202"]
    assert list(runs["surface"]) == ["芝", "芝", "ダート"]
    assert runs["finish"].astype("Int64").tolist()[:2] == [1, 2] and runs["finish"].isna().tolist() == [False, False, True]
    assert runs["corner"].iloc[0] == 2 and runs["corner"].isna().tolist() == [False, True, True]


def test_4コーナーの順位が無ければ_前のコーナーの順位() -> None:
    con = duckdb.connect()
    make_tables(con, [])
    con.execute(f"INSERT INTO ra VALUES ({', '.join('?' for _ in _RA)})", ["7", "20261108", "2026", "1108", "08", "05", "02", "01", "10"])
    con.execute(f"INSERT INTO se VALUES ({', '.join('?' for _ in _SE)})",
                ["7", "20261108", "2026", "1108", "08", "05", "02", "01", "01", "01", "00", "00", "03", "00"])
    assert list(VenueRunRepository(con).read("08", date(2026, 11, 8), date(2026, 11, 8))["corner"]) == [3]
