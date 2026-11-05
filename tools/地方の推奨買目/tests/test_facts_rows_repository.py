"""FactsRowsRepository（事実表から当てはめ用の出走の行）のテスト。事実表は作らず、同じ名前の一時表を先に置く。"""

from __future__ import annotations

from datetime import date

import duckdb

from 共通.facts import FACTS_TABLE

from 地方の推奨買目.repository import FactsRowsRepository


def test_期間と頭数で絞り_出走した馬だけ():
    con = duckdb.connect()
    con.execute(f"CREATE TEMP TABLE {FACTS_TABLE} (race_id VARCHAR, race_date VARCHAR, field_size INTEGER, frame_no INTEGER, horse_no INTEGER, "
                "popularity INTEGER, win_odds DOUBLE, finish INTEGER, ran BOOLEAN)")
    con.executemany(f"INSERT INTO {FACTS_TABLE} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        ("2024010145110101", "2024-01-01", 12, 1, 1, 3, 5.0, 1, True),
        ("2024010145110101", "2024-01-01", 12, 1, 2, 1, 2.0, None, False),   # 取消
        ("2023123145110101", "2023-12-31", 12, 1, 1, 3, 5.0, 1, True),      # 期間の前
        ("2024010145110102", "2024-01-01", 8, 1, 1, 3, 5.0, 1, True),       # 頭数が足りない
    ])
    rows = FactsRowsRepository(con).load(date(2024, 1, 1), 11)
    assert list(rows["race_id"]) == ["2024010145110101"] and list(rows["horse_no"]) == [1]
    assert list(rows.columns) == ["race_id", "race_date", "field_size", "frame_no", "horse_no", "popularity", "win_odds", "finish"]
