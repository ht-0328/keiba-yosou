"""重賞の、その重賞の過去の開催の出走馬を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import stakes

from .target_scope import TargetScope


class StakesTendencyRepository:
    """対象のレースのうち重賞（G1・G2・G3）について、同じ重賞（特別競走番号）のそのレースより前の開催の出走馬を読む
    （1行 = 対象のレース × 過去の開催の1頭）。対象の馬の行（前走のレースの鍵だけを持つ）も付く。

    SQL（レースの同定・リークなし・前走のレースの鍵）は ``tools/共通/stakes.py`` の ``edition_runners_sql`` にあり、
    重賞の傾向を特徴量にする予想（重賞の傾向と近走から3着以内を予想）が、「自分と同じ条件だった馬の成績」（まとまり K）を
    数えるのに使う。重賞でないレースの行は返さないので、対象に平場が混ざっていてもよい。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``tools/共通/stakes.py`` の ``edition_runners_sql`` の返す列（target_race_id・is_target・race_id・stakes_no・
        race_date・horse_id・``RUNNER_COLUMNS``・prev_key）。``race_date`` は日付型、ID は文字列。"""
        stakes.ensure_stakes_map(self._con)
        frame = self._con.execute(stakes.edition_runners_sql(scope.relation)).df()
        return frame.assign(
            race_date=pd.to_datetime(frame["race_date"]),
            target_race_id=frame["target_race_id"].astype(str), race_id=frame["race_id"].astype(str),
            horse_id=frame["horse_id"].astype(str),
        )
