"""組み合わせの券種（馬連・馬単・ワイド・3連複・3連単）の払戻を、払戻の子の表から読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys
from 共通.filters import Filters

from 決着の型.ticket_kind import TicketKind

#: 払戻の子の表の列（無いときの空の関係を作るのに使う）。
_PAYOUT_COLUMNS = (*keys.RACE_KEY, "_連番", "組番", "払戻金")
#: 組番の中の馬番の桁数。
_DIGITS_PER_HORSE = 2


class ComboPayoutRepository:
    """1つの券種の払戻を、条件に合うレースぶん読む（1行 = 1つの組番）。

    列は ``race_id``・``combo``（馬番の組。順番は組番のまま）・``yen``（100円あたりの円）。
    同じ組番の行が重なっていれば大きいほうを取る。払戻金が 0 の空きの行は落とす。
    ワイドの3行・同着の複数行はそのまま返し、まとめるのは精算の側。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, kind: TicketKind, filters: Filters = Filters()) -> pd.DataFrame:
        facts.ensure_facts(self._con)
        table = facts.optional_relation(self._con, kind.payout_table, _PAYOUT_COLUMNS)
        where, params = filters.where()
        yen = f"TRY_CAST({keys.q('払戻金')} AS BIGINT)"
        sql = f"""
        SELECT {keys.rid_expr()} AS race_id, trim({keys.q('組番')}) AS combo_text, max({yen}) AS yen
        FROM {table}
        WHERE {keys.jra_only()} AND {yen} > 0
          AND {keys.rid_expr()} IN (SELECT DISTINCT race_id FROM {facts.FACTS_TABLE} WHERE ran AND {where})
        GROUP BY ALL
        ORDER BY race_id, combo_text
        """
        rows = self._con.execute(sql, params).df()
        rows["combo"] = rows["combo_text"].map(self._split)
        return rows.drop(columns="combo_text")

    @staticmethod
    def _split(text: str) -> tuple[int, ...]:
        """組番（馬番を2桁ずつ並べた文字列）を馬番の組にする。"""
        return tuple(int(text[i:i + _DIGITS_PER_HORSE]) for i in range(0, len(text), _DIGITS_PER_HORSE))
