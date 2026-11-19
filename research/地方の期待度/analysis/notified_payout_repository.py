"""1つの券種の払戻を、開催日の範囲で読む（1 SQL のひな形を券種で埋める）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

#: 券種 → (払戻の表, 組の列, 1つの番号の桁数)。枠連は枠番1桁ずつ、ほかの組番は馬番2桁ずつ。
_SPECS: dict[str, tuple[str, str, int]] = {
    "単勝": ("hr__単勝払戻", "馬番", 2), "複勝": ("hr__複勝払戻", "馬番", 2), "枠連": ("hr__枠連払戻", "組番", 1),
    "馬連": ("hr__馬連払戻", "組番", 2), "ワイド": ("hr__ワイド払戻", "組番", 2), "馬単": ("hr__馬単払戻", "組番", 2),
    "3連複": ("hr__3連複払戻", "組番", 2), "3連単": ("hr__3連単払戻", "組番", 2),
}
TICKETS: tuple[str, ...] = tuple(_SPECS)


@dataclass(frozen=True)
class NotifiedPayoutRepository:
    """``race_id``（16桁の文字列）・``numbers``（馬番か枠番の組）・``payout``（100円あたりの円）。``day_from``〜``day_to`` は YYYYMMDD（両端を含む）。
    同じ組の行が重なっていれば大きいほうを取る。"""

    con: duckdb.DuckDBPyConnection

    def load(self, ticket: str, day_from: str, day_to: str) -> pd.DataFrame:
        table, column, width = _SPECS[ticket]
        yen = f"TRY_CAST({keys.q('払戻金')} AS BIGINT)"
        sql = f"""
            SELECT {keys.rid_expr()} AS race_id, trim({keys.q(column)}) AS combo, max({yen}) AS payout
            FROM {keys.q(table)}
            WHERE 開催年 || 開催月日 BETWEEN ? AND ? AND {yen} > 0 AND TRY_CAST(trim({keys.q(column)}) AS BIGINT) > 0
            GROUP BY ALL
        """
        rows = self.con.execute(sql, [day_from, day_to]).df()
        numbers = rows["combo"].map(lambda combo: tuple(int(combo[i:i + width]) for i in range(0, len(combo), width)))
        return rows.assign(numbers=numbers).drop(columns="combo")
