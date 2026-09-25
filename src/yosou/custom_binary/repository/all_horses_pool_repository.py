"""馬連・ワイド・3連複・複勝のオッズから、馬ごとの「組に入る確率」を読む。"""

import duckdb
import pandas as pd

from .pool_odds_rows import pool_odds_rows
from .pool_spec import PoolSpec


class AllHorsesPoolRepository:
    """順不同の券種なので、組に入っている馬すべてに、その買い目の確率を配って足す。

    例: 3連複で4番を含む買い目の確率を全部足すと、3連複のプールから見た4番の3着以内率になる。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, spec: PoolSpec, scope_relation: str) -> pd.DataFrame:
        """1行 = 1頭。列は ``race_id``・``horse_no``・``spec.column``。"""
        sql = f"""
        WITH {pool_odds_rows(self._con, spec, scope_relation)}, split AS (
            SELECT odds.race_id,
                   TRY_CAST(substr(odds.combo, (place.i - 1) * 2 + 1, 2) AS INTEGER) AS horse_no, odds.inverse
            FROM odds CROSS JOIN (SELECT unnest(range(1, {spec.horses} + 1)) AS i) AS place
        )
        SELECT split.race_id, split.horse_no, sum(split.inverse) / max(totals.total) * {spec.scale} AS {spec.column}
        FROM split JOIN totals USING (race_id)
        GROUP BY split.race_id, split.horse_no
        """
        return self._con.execute(sql).df()
