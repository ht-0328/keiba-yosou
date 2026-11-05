"""券種（単勝・複勝・枠連・馬連・ワイド・馬単・3連複）の払戻を、指定したレースについて読む（1 SQL のひな形を券種で埋める）。同着は組ごとに足す。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

from 地方の推奨買目.repository.ticket_odds_repository import combo_columns

_RACES_VIEW = "_ticket_payout_races"
#: 券種 → (払戻表, 組の列の作り方)。
_SPECS: dict[str, tuple[str, str]] = {
    "単勝": ("hr__単勝払戻", "馬番"), "複勝": ("hr__複勝払戻", "馬番"), "枠連": ("hr__枠連払戻", "枠"), "馬連": ("hr__馬連払戻", "組番2"),
    "ワイド": ("hr__ワイド払戻", "組番2"), "馬単": ("hr__馬単払戻", "組番2"), "3連複": ("hr__3連複払戻", "組番3"),
}


@dataclass(frozen=True)
class LocalTicketPayoutRepository:
    """``race_id``（16桁の整数）・``a``（・``b``・``c``）・``payout``（100円あたりの払戻、円）。的中の組だけ。"""

    con: duckdb.DuckDBPyConnection
    ticket: str

    def load(self, race_ids: pd.Series) -> pd.DataFrame:
        table, kind = _SPECS[self.ticket]
        self.con.register(_RACES_VIEW, pd.DataFrame({"race_id": race_ids.astype(str).unique()}))
        columns = combo_columns(kind, "p")
        names = ["a", "b", "c"][:len(columns)]
        sql = f"""
            SELECT race_id, {', '.join(names)}, SUM(payout) AS payout
            FROM (
                SELECT CAST({keys.rid_expr('p')} AS BIGINT) AS race_id, {', '.join(columns)}, CAST(p.払戻金 AS INTEGER) AS payout
                FROM {keys.q(table)} p
                JOIN {_RACES_VIEW} r ON r.race_id = {keys.rid_expr('p')}
                WHERE CAST(p.払戻金 AS INTEGER) > 0
            )
            GROUP BY race_id, {', '.join(names)}
        """
        try:
            return self.con.execute(sql).df()
        finally:
            self.con.unregister(_RACES_VIEW)
