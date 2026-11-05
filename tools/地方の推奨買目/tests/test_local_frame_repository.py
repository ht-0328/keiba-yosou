"""LocalFrameRepository（地方の元DB の出走馬の表から 馬番 → 枠番）のテスト。メモリ上の DuckDB に架空の行を入れる。"""

from __future__ import annotations

import duckdb

from 地方の推奨買目.repository.local_frame_repository import LocalFrameRepository

_COLUMNS = ("データ区分", "データ作成年月日", "開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"',
            "レース番号", "枠番", "馬番")


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"CREATE TABLE se ({', '.join(f'{name} VARCHAR' for name in _COLUMNS)})")
    rows = [
        ("1", "20261104", "2026", "1105", "50", "08", "03", "05", "1", "01"),
        ("7", "20261105", "2026", "1105", "50", "08", "03", "05", "1", "01"),  # 同じ馬の新しい行
        ("7", "20261105", "2026", "1105", "50", "08", "03", "05", "5", "06"),
        ("7", "20261105", "2026", "1105", "50", "08", "03", "05", " ", "07"),  # 枠番が無い
        ("7", "20261105", "2026", "1105", "50", "08", "03", "06", "2", "01"),  # 別のレース
    ]
    con.executemany(f"INSERT INTO se VALUES ({', '.join('?' for _ in _COLUMNS)})", rows)
    return con


def test_そのレースの馬番ごとの枠番_新しい行だけ_枠番の無い馬は含めない() -> None:
    assert LocalFrameRepository(_db()).read("2026110550080305") == {1: 1, 6: 5}
