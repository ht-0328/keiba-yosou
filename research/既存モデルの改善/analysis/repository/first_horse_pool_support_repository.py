"""1着の馬だけを見る券種から、馬ごとの支持を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import keys

from .pool_spec import PoolSpec

#: 確定オッズのデータ区分（4 確定・5 確定(月曜)）。
_FINAL = "('4', '5')"


class FirstHorsePoolSupportRepository:
    """馬単・3連単の確定オッズから、馬ごとの支持（その馬が1着の組の確率の和 = 市場が見た勝率）を読む（1 SQL）。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, spec: PoolSpec) -> None:
        self._con = con
        self._spec = spec

    def read(self, first_day: date) -> pd.DataFrame:
        """列は ``race_id``・``horse_no``・``spec.column``。"""
        spec = self._spec
        join = " AND ".join(f"o.{keys.q(name)} = h.{keys.q(name)}" for name in (*keys.RACE_KEY, "発表月日時分"))
        sql = f"""
        WITH header AS (
            SELECT {keys.key_list('h')}, h."発表月日時分"
            FROM {keys.q(spec.parent)} AS h
            WHERE h."データ区分" IN {_FINAL} AND {keys.jra_only('h')} AND h."開催年" >= ?
            {keys.latest_qualify(keys.RACE_KEY, 'h')}
        ), priced AS (
            SELECT {keys.rid_expr('o')} AS race_id, TRY_CAST(substr(trim(o.{keys.q(spec.combo)}), 1, 2) AS INTEGER) AS horse_no,
                   1.0 / ({spec.price}) AS inverse
            FROM {keys.q(spec.child)} AS o JOIN header AS h ON {join}
            WHERE ({spec.price}) > 0
        ), totals AS (
            SELECT race_id, sum(inverse) AS total FROM priced GROUP BY race_id
        )
        SELECT priced.race_id, priced.horse_no, sum(priced.inverse) / max(totals.total) AS "{spec.column}"
        FROM priced JOIN totals USING (race_id)
        GROUP BY priced.race_id, priced.horse_no
        """
        return self._con.execute(sql, [str(first_day.year)]).df()
