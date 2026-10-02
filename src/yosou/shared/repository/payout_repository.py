"""1つの券種の払戻の明細を、期間ぶん読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from ..betting import TicketType
from .race_day_range import RaceDayRange

#: 出力の列。
COMBO, YEN, POPULARITY, SEQ = "combo", "yen", "popularity", "seq"


class PayoutRepository:
    """1つの券種の払戻の明細を、期間の全レースぶん 1組番1行で読む（``hr__<券種>払戻``）。

    複勝（2〜3行）・ワイド（3行）は複数行が正常で、ほかの券種の複数行は同着。どれも行のまま返し、まとめない
    （買い目との照合は、使う側の精算のクラス）。空き繰り返しの行（払戻金 0）は落とす。
    列は ``race_id``・``combo``（馬番か組番。2桁ずつ）・``yen``（100円あたりの円）・``popularity``（その組み合わせの人気順）・``seq``（連番）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, ticket_type: TicketType) -> None:
        self._con = con
        self._ticket_type = ticket_type

    def read(self, days: RaceDayRange) -> pd.DataFrame:
        spec = self._ticket_type.spec
        table = facts.optional_relation(self._con, spec.payout_table, (*keys.RACE_KEY, "_連番", spec.combo_column, "払戻金", "人気順"))
        yen = f"TRY_CAST({keys.col('払戻金', 'p')} AS BIGINT)"
        sql = f"""
        SELECT {keys.rid_expr('p')} AS race_id, trim({keys.col(spec.combo_column, 'p')}) AS {COMBO}, {yen} AS {YEN},
               TRY_CAST({keys.col('人気順', 'p')} AS INTEGER) AS {POPULARITY}, TRY_CAST({keys.col('_連番', 'p')} AS INTEGER) AS {SEQ}
        FROM {table} AS p
        WHERE {keys.jra_only('p')} AND {days.condition('p')} AND {yen} > 0
        ORDER BY race_id, {SEQ}
        """
        return self._con.execute(sql, days.params).df()
