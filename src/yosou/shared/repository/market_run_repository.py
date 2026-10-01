"""市場に対する成績を数えるための、過去の全出走（オッズと着順）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts

from .target_scope import TargetScope


class MarketRunRepository:
    """過去の平地の全出走（出走した馬だけ。1行 = 1頭）を、単勝オッズ・着順・騎手・調教師・父・母父の列で読む。

    騎手・調教師・血統の「市場に対する成績」（オッズから期待された3着以内率をどれだけ上回ったか）の材料になる。
    オッズから見た3着以内率はレースの全頭のオッズから出すので、対象の人に関わるレースだけでなく、期間の全レースを読む。
    期間は、対象のいちばん早い開催日の ``window_days`` 日前から、いちばん遅い開催日の前日まで。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, window_days: int) -> None:
        self._con = con
        self._window_days = window_days

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``race_id``・``race_date``・``win_odds``・``finish``・``jockey_code``・``trainer_code``・``sire``・``damsire``。
        開催日・レースID・馬番の順に並べる。"""
        first_race_day = f"(SELECT min(CAST(race_date AS DATE)) FROM {scope.relation})"
        sql = f"""
        SELECT race_id, CAST(race_date AS DATE) AS race_date, win_odds, finish,
               jockey_code, trainer_code, sire, damsire
        FROM {facts.FACTS_TABLE}
        WHERE ran AND surface <> '障害'
          AND race_date < (SELECT max(race_date) FROM {scope.relation})
          AND CAST(race_date AS DATE) >= {first_race_day} - {self._window_days}
        ORDER BY race_date, race_id, horse_no
        """
        frame = self._con.execute(sql).df()
        return frame.assign(race_date=pd.to_datetime(frame["race_date"]))
