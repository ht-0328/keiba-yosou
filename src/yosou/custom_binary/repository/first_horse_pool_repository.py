"""馬単・3連単のオッズから、馬ごとの「1着になる確率」を読む。"""

import duckdb
import pandas as pd

from .pool_odds_rows import pool_odds_rows
from .pool_spec import PoolSpec


class FirstHorsePoolRepository:
    """組番の先頭の馬（1着の馬）ごとに、買い目の確率（1/オッズ をレース内で合計1にそろえた値）を足す。

    例: 3連単で「4番が1着」の買い目の確率を全部足すと、3連単のプールから見た4番の勝率になる。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, spec: PoolSpec, scope_relation: str) -> pd.DataFrame:
        """1行 = 1頭。列は ``race_id``・``horse_no``・``spec.column``。"""
        sql = f"""
        WITH {pool_odds_rows(self._con, spec, scope_relation)}
        SELECT odds.race_id, TRY_CAST(substr(odds.combo, 1, 2) AS INTEGER) AS horse_no,
               sum(odds.inverse) / max(totals.total) * {spec.scale} AS {spec.column}
        FROM odds JOIN totals USING (race_id)
        GROUP BY odds.race_id, substr(odds.combo, 1, 2)
        """
        return self._con.execute(sql).df()
