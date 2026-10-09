"""距離の変更の傾向（まとまり R）を数えるための、過去の平地の全出走を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, keys, stakes

from .target_scope import TargetScope


class DistanceChangeRunRepository:
    """過去の平地の全出走（出走した馬だけ。1行 = 1頭）を、コース・距離の変更・単勝オッズ・人気・着順・特別競走番号の列で読む。

    同じコースで同じ距離の変更だった馬が、オッズの期待よりどれだけ走ったかを数える材料。オッズから見た率はレースの全頭の
    オッズから出すので、期間の全レースを読む。期間は ``first_day`` から、対象のいちばん遅い開催日の前日まで
    （コースの傾向は全期間で数えるので、窓で切らない）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, first_day: date) -> None:
        self._con = con
        self._first_day = first_day

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``race_id``・``race_date``（日付型）・``venue``・``course``・``distance_m``・``distance_change``・``popularity``・
        ``win_odds``・``finish``・``stakes_no``。開催日・レースID・馬番の順に並べる。"""
        stakes_map = stakes.ensure_stakes_map(self._con)
        sql = f"""
        SELECT f.race_id, CAST(f.race_date AS DATE) AS race_date, f.venue, f.course, f.distance_m, f.distance_change,
               f.popularity, f.win_odds, f.finish, m.stakes_no
        FROM {facts.FACTS_TABLE} AS f
        LEFT JOIN {keys.q(stakes_map)} AS m USING (race_id)
        WHERE f.ran AND f.surface <> '障害'
          AND f.race_date >= '{self._first_day.isoformat()}'
          AND f.race_date < (SELECT max(race_date) FROM {scope.relation})
        ORDER BY f.race_date, f.race_id, f.horse_no
        """
        frame = self._con.execute(sql).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
