"""LocalRaceRepository（地方の元DB のレース情報からその日のレースを読む）のテスト。メモリ上の DuckDB に架空の行を入れる。"""

from __future__ import annotations

import duckdb

from 発走前の通知.local_race_repository import LocalRaceRepository

_COLUMNS = ("レコード種別ID", "データ区分", "データ作成年月日", "開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"',
            "レース番号", "競走名本題", "発走時刻")


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"CREATE TABLE ra ({', '.join(f'{name} VARCHAR' for name in _COLUMNS)})")
    rows = [
        ("RA", "1", "20261104", "2026", "1105", "47", "15", "04", "01", "", "1020"),  # 古い出馬表（発走時刻が変わる前）
        ("RA", "2", "20261105", "2026", "1105", "47", "15", "04", "01", "", "1025"),
        ("RA", "2", "20261105", "2026", "1105", "50", "08", "03", "01", "テスト特別  ", "1040"),
        ("RA", "2", "20261105", "2026", "1105", "83", "01", "01", "01", "", "1100"),  # ばんえい
        ("RA", "2", "20261105", "2026", "1106", "47", "15", "05", "01", "", "1025"),  # 別の日
    ]
    con.executemany(f"INSERT INTO ra VALUES ({', '.join('?' for _ in _COLUMNS)})", rows)
    return con


def test_その日の地方のレースを_新しい行だけ_発走の順に_ばんえいは除く() -> None:
    rows = LocalRaceRepository(_db()).read("2026-11-05")
    assert [(row.rid, row.venue_code, row.number, row.name, row.post) for row in rows] == [
        ("2026110547150401", "47", 1, "", "1025"),
        ("2026110550080301", "50", 1, "テスト特別", "1040"),
    ]
