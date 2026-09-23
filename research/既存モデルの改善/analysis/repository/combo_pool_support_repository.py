"""組の全部の馬に配る券種から、馬ごとの支持を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import keys

from .pool_spec import PoolSpec

#: 確定オッズのデータ区分（4 確定・5 確定(月曜)）。
_FINAL = "('4', '5')"


class ComboPoolSupportRepository:
    """複勝・馬連・ワイド・3連複の確定オッズから、馬ごとの支持を読む（1 SQL）。

    オッズの逆数をレース内で合計 1 にそろえると、市場がその組に付けた確率になる。それを、組に入っている馬ごとに足す。
    例: 3連複なら「その馬を含む組の確率の和」= 市場が見た、その馬が3着以内に入る確率（の目安）。
    """

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
            SELECT {keys.rid_expr('o')} AS race_id, trim(o.{keys.q(spec.combo)}) AS combo, 1.0 / ({spec.price}) AS inverse
            FROM {keys.q(spec.child)} AS o JOIN header AS h ON {join}
            WHERE ({spec.price}) > 0
        ), totals AS (
            SELECT race_id, sum(inverse) AS total FROM priced GROUP BY race_id
        ), spread AS (
            SELECT race_id, TRY_CAST(substr(combo, (slot.i - 1) * 2 + 1, 2) AS INTEGER) AS horse_no, inverse
            FROM priced CROSS JOIN (SELECT unnest(range(1, {spec.horses} + 1)) AS i) AS slot
        )
        SELECT spread.race_id, spread.horse_no, sum(spread.inverse) / max(totals.total) AS "{spec.column}"
        FROM spread JOIN totals USING (race_id)
        GROUP BY spread.race_id, spread.horse_no
        """
        return self._con.execute(sql, [str(first_day.year)]).df()
