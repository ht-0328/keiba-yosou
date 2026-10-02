"""重賞のレースごとの傾向（それより前の開催の数え上げ）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import stakes

from .target_scope import TargetScope


class StakesTendencyRepository:
    """対象のレースのうち重賞（G1・G2・G3）について、そのレースより前の開催から数えた傾向を、1行 = 1レースで読む。

    数え上げの定義（切り口・基準・リークなし）は ``tools/共通/stakes.py`` にあり、分析ツール
    （``tools/重賞攻略/``）と同じもの。重賞の傾向を特徴量にする予想（重賞の傾向と近走から3着以内を予想）が使う。
    重賞でないレースの行は返さないので、対象に平場が混ざっていてもよい。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``tools/共通/stakes.py`` の ``tendency_sql`` の返す列（race_id・editions・*_n・*_hits・base_*）。"""
        stakes.ensure_stakes_map(self._con)
        return self._con.execute(stakes.tendency_sql(scope.relation)).df()
