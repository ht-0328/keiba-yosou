"""距離の変更の傾向（まとまり R）を付ける対象の出走を、コース・距離の変更・前走の距離・特別競走番号の列で読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import keys, stakes

from .target_scope import TargetScope


class DistanceChangeTargetRepository:
    """対象の出走（1行 = 1頭）を、``race_id``・``horse_id``・``race_date``（日付型）・``venue``・``course``・``distance_m``・
    ``distance_change``・``prev_distance_m``・``stakes_no``（重賞でなければ欠損値）の列で読む。

    特別競走番号は重賞の対応表（``tools/共通/stakes.py``。確定前の出馬表の行も入る）から引く。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        stakes_map = stakes.ensure_stakes_map(self._con)
        sql = f"""
        SELECT t.race_id, t.horse_id, CAST(t.race_date AS DATE) AS race_date, t.venue, t.course, t.distance_m,
               t.distance_change, t.prev_distance_m, m.stakes_no
        FROM {scope.relation} AS t
        LEFT JOIN {keys.q(stakes_map)} AS m USING (race_id)
        WHERE t.horse_id IS NOT NULL
        ORDER BY t.race_date, t.race_id, t.horse_id
        """
        frame = self._con.execute(sql).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
