"""枠連の確定オッズ・払戻と、馬番 → 枠番 を元DB から読む（本番の部品に枠連の券種が無いので、同じ作りでここに書く）。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import keys

from yosou.shared.repository import RaceDayRange

#: 確定オッズのデータ区分（本番の ``FinalOddsRepository`` と同じ。4 確定・5 確定(月曜)）。
_FINAL_STAGES: tuple[str, ...] = ("4", "5")
_ANNOUNCED = "発表月日時分"


class BracketSource:
    """枠連（``o1`` の子 ``o1__枠連オッズ``・``hr__枠連払戻``）と枠番（``se``）を、期間の中央のレースぶん読む。

    オッズは親（``o1``）をデータ区分 4・5 に絞って1レース1行にし、その発表月日時分で子と結ぶ（``FinalOddsRepository`` と同じ）。
    組番は枠の番号を1桁ずつ並べた2文字（例 ``"18"`` = 1枠と8枠）。オッズは10倍の整数（``'00479'`` = 47.9倍）、0 は無投票。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def odds(self, days: RaceDayRange) -> pd.DataFrame:
        """列 ``race_id``・``combo``・``odds``。"""
        join = " AND ".join(f"{keys.col(column, 'o')} = {keys.col(column, 'h')}" for column in (*keys.RACE_KEY, _ANNOUNCED))
        sql = f"""
        WITH final_header AS (
            SELECT {keys.key_list('h')}, {keys.col(_ANNOUNCED, 'h')}
            FROM o1 AS h
            WHERE {keys.col('データ区分', 'h')} IN {keys.sql_list(_FINAL_STAGES)} AND {keys.jra_only('h')} AND {days.condition('h')}
            {keys.latest_qualify(keys.RACE_KEY, 'h')}
        )
        SELECT {keys.rid_expr('o')} AS race_id, trim({keys.col('組番', 'o')}) AS combo,
               NULLIF(TRY_CAST({keys.col('オッズ', 'o')} AS INTEGER), 0) / 10.0 AS odds
        FROM "o1__枠連オッズ" AS o JOIN final_header AS h ON {join}
        """
        frame = self._con.execute(sql, days.params).df()
        return frame[frame["odds"].notna()].reset_index(drop=True)

    def payouts(self, days: RaceDayRange) -> pd.DataFrame:
        """列 ``race_id``・``combo``・``payout``（100円あたりの円。同着で複数行なら組ごとに足す）。"""
        yen = f"TRY_CAST({keys.col('払戻金', 'p')} AS BIGINT)"
        sql = f"""
        SELECT {keys.rid_expr('p')} AS race_id, trim({keys.col('組番', 'p')}) AS combo, sum({yen}) AS payout
        FROM "hr__枠連払戻" AS p
        WHERE {keys.jra_only('p')} AND {days.condition('p')} AND {yen} > 0
        GROUP BY ALL
        """
        return self._con.execute(sql, days.params).df()

    def frames(self, days: RaceDayRange) -> pd.DataFrame:
        """列 ``race_id``・``horse_no``・``frame``（馬番と枠番）。"""
        sql = f"""
        SELECT {keys.rid_expr('s')} AS race_id, TRY_CAST({keys.col('馬番', 's')} AS INTEGER) AS horse_no,
               any_value(TRY_CAST({keys.col('枠番', 's')} AS INTEGER)) AS frame
        FROM se AS s
        WHERE {keys.jra_only('s')} AND {days.condition('s')} AND TRY_CAST({keys.col('枠番', 's')} AS INTEGER) > 0
        GROUP BY ALL
        """
        return self._con.execute(sql, days.params).df()
