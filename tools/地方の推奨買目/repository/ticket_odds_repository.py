"""券種（単勝・複勝・枠連・馬連・ワイド・馬単・3連複）の確定オッズを、指定したレースの全部の組について読む（1 SQL のひな形を券種で埋める）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

_FINAL = "5"
_RACES_VIEW = "_ticket_odds_races"
#: 券種 → (ヘッダ表, 明細表, 組の列の作り方, オッズの列)。組番は馬番 2桁ずつ（枠連は枠番 1桁ずつ）。複勝・ワイドはオッズが幅（最低・最高）。
_SPECS: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "単勝": ("o1", "o1__単勝オッズ", "馬番", ("オッズ",)),
    "複勝": ("o1", "o1__複勝オッズ", "馬番", ("最低オッズ", "最高オッズ")),
    "枠連": ("o1", "o1__枠連オッズ", "枠", ("オッズ",)),
    "馬連": ("o2", "o2__馬連オッズ", "組番2", ("オッズ",)),
    "ワイド": ("o3", "o3__ワイドオッズ", "組番2", ("最低オッズ", "最高オッズ")),
    "馬単": ("o4", "o4__馬単オッズ", "組番2", ("オッズ",)),
    "3連複": ("o5", "o5__3連複オッズ", "組番3", ("オッズ",)),
}


def combo_columns(kind: str, alias: str, column: str = "組番") -> list[str]:
    """組の列の SQL（``a``・``b``・``c``）。``kind`` は 馬番・枠・組番2・組番3。"""
    if kind == "馬番":
        return [f"CAST({alias}.馬番 AS INTEGER) AS a"]
    if kind == "枠":
        return [f"CAST(substr({alias}.{column}, 1, 1) AS INTEGER) AS a", f"CAST(substr({alias}.{column}, 2, 1) AS INTEGER) AS b"]
    n = 2 if kind == "組番2" else 3
    return [f"CAST(substr({alias}.{column}, {1 + i * 2}, 2) AS INTEGER) AS {'abc'[i]}" for i in range(n)]


@dataclass(frozen=True)
class LocalTicketOddsRepository:
    """``race_id``（16桁の整数）・``a``（・``b``・``c``）・``odds``（倍。複勝・ワイドは ``odds_lo``・``odds_hi``）。発売の無い組は出ない。"""

    con: duckdb.DuckDBPyConnection
    ticket: str

    def load(self, race_ids: pd.Series) -> pd.DataFrame:
        head, detail, kind, odds_columns = _SPECS[self.ticket]
        self.con.register(_RACES_VIEW, pd.DataFrame({"race_id": race_ids.astype(str).unique()}))
        key_join = " AND ".join(f"d.{keys.q(name)} = h.{keys.q(name)}" for name in keys.RACE_KEY)
        if len(odds_columns) == 1:
            odds_sql = f"TRY_CAST(d.{keys.q(odds_columns[0])} AS DOUBLE) / 10.0 AS odds"
        else:
            odds_sql = (f"TRY_CAST(d.{keys.q(odds_columns[0])} AS DOUBLE) / 10.0 AS odds_lo, "
                        f"TRY_CAST(d.{keys.q(odds_columns[1])} AS DOUBLE) / 10.0 AS odds_hi")
        sql = f"""
            SELECT CAST({keys.rid_expr('h')} AS BIGINT) AS race_id, {', '.join(combo_columns(kind, 'd'))}, {odds_sql}
            FROM {head} h
            JOIN {keys.q(detail)} d ON {key_join} AND d.発表月日時分 = h.発表月日時分
            JOIN {_RACES_VIEW} r ON r.race_id = {keys.rid_expr('h')}
            WHERE h.データ区分 = '{_FINAL}' AND TRY_CAST(d.{keys.q(odds_columns[0])} AS DOUBLE) > 0
        """
        try:
            return self.con.execute(sql).df()
        finally:
            self.con.unregister(_RACES_VIEW)
