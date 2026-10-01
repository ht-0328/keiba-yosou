"""対戦型データマイニング予想の予測スコアを、``tm`` の子の表から直接読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

_COLUMNS = ("開催年", "開催月日", "競馬場コード", "開催回[第N回]", "開催日目[N日目]", "レース番号", "馬番", "予測スコア")


class MiningScoreRepository:
    """1行 = 1頭（``rid``・``horse_no``・``tm_score``）。予測スコアは 10 倍の整数なので 10 で割る。0 と空は予想なし。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self) -> pd.DataFrame:
        table = facts.optional_relation(self._con, "tm__マイニング予想", _COLUMNS)
        return self._con.execute(f"""
            SELECT "開催年" || "開催月日" || "競馬場コード" || "開催回[第N回]" || "開催日目[N日目]" || "レース番号" AS rid,
                   TRY_CAST("馬番" AS INTEGER) AS horse_no,
                   max(TRY_CAST("予測スコア" AS INTEGER)) / 10.0 AS tm_score
            FROM {table}
            WHERE TRY_CAST("馬番" AS INTEGER) > 0 AND TRY_CAST("予測スコア" AS INTEGER) > 0
            GROUP BY 1, 2
        """).fetchdf()
