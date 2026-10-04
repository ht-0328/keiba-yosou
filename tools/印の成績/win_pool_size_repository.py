"""レースごとの単勝の売上（票数合計）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

#: オッズ1（単複枠）の親。確定の断面に票数合計が入る。
_HEADER_TABLE = "o1"
_VOTES = "単勝票数合計"
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", _VOTES)
#: 確定の断面のデータ区分（4 確定・5 確定(月曜)）。
_FINAL_STAGES: tuple[str, ...] = ("4", "5")
#: 読むレースIDを入れる一時表。
_WANTED = "mark_stats_pool_size_races"
#: 出す列（票。1票 = 100円）。
WIN_POOL = "win_pool"


class WinPoolSizeRepository:
    """``race_ids`` のレースの、確定の単勝の票数合計を1レース1行で読む（研究「回収率100超の施策」の施策4。売上の小さいレースほど
    値付けが粗いはず、という見立てを確かめるのに使う）。

    列は race_id・``win_pool``（票。1票 = 100円）。確定の断面が無いレースは行が無い。
    """

    def read(self, con: duckdb.DuckDBPyConnection, race_ids: pd.Series) -> pd.DataFrame:
        header = facts.optional_relation(con, _HEADER_TABLE, _HEADER_COLUMNS)
        con.register("mark_stats_pool_size_race_ids", pd.DataFrame({"race_id": race_ids.astype(str).drop_duplicates()}))
        con.execute(f"CREATE OR REPLACE TEMP TABLE {_WANTED} AS SELECT * FROM mark_stats_pool_size_race_ids")
        sql = f"""
            SELECT {keys.rid_expr('h')} AS race_id, max(TRY_CAST(h.{keys.q(_VOTES)} AS DOUBLE)) AS {WIN_POOL}
            FROM {header} AS h
            WHERE {keys.rid_expr('h')} IN (SELECT race_id FROM {_WANTED})
              AND h.{keys.q('データ区分')} IN {keys.sql_list(_FINAL_STAGES)}
            GROUP BY {keys.rid_expr('h')}
        """
        return con.execute(sql).df().astype({"race_id": str})
