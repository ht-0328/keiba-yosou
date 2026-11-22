"""RaceJockeyRepository（元DB の出走馬の表から 馬番 → 騎手名）のテスト。メモリ上の DuckDB に架空の行を入れる。"""

from __future__ import annotations

import duckdb

from 発走前の通知.race_jockey_repository import RaceJockeyRepository

_COLUMNS = ("データ区分", "データ作成年月日", "開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"',
            "レース番号", "馬番", "騎手名略称")


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"CREATE TABLE se ({', '.join(f'{name} VARCHAR' for name in _COLUMNS)})")
    rows = [
        ("1", "20261121", "2026", "1122", "08", "05", "06", "11", "01", "騎手Ａ"),
        ("2", "20261122", "2026", "1122", "08", "05", "06", "11", "01", "騎手Ｂ　"),  # 乗り替わり（新しい行）
        ("2", "20261122", "2026", "1122", "08", "05", "06", "11", "02", "騎手　Ｃ"),
        ("2", "20261122", "2026", "1122", "08", "05", "06", "11", "03", "　"),  # 騎手が無い
        ("2", "20261122", "2026", "1122", "08", "05", "06", "10", "01", "騎手Ｄ"),  # 別のレース
    ]
    con.executemany(f"INSERT INTO se VALUES ({', '.join('?' for _ in _COLUMNS)})", rows)
    return con


def test_そのレースの馬番ごとの騎手_新しい行だけ_空白を除き_騎手の無い馬は含めない() -> None:
    assert RaceJockeyRepository(_db()).read("2026112208050611") == {1: "騎手Ｂ", 2: "騎手Ｃ"}
