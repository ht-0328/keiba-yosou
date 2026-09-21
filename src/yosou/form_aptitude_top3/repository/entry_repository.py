"""出走の行を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from .target_scope import TargetScope

#: 読む事実表の列（意味は ``tools/共通/facts.py`` の ``FACT_COLUMNS``）。
_COLUMNS: tuple[str, ...] = (
    # レース
    "race_id", "month", "venue_code", "venue", "surface", "course", "distance_m",
    "condition_code", "condition", "class_order", "field_size", "mixed_sex",
    # 馬
    "horse_id", "horse_name", "sex", "age", "affiliation", "frame_no", "horse_no", "carried",
    "body_weight", "weight_change", "blinker",
    # 騎手と調教師
    "jockey_code", "apprentice", "jockey_change", "trainer_code",
    # 前走
    "prev_finish", "prev_time_diff", "prev_popularity", "prev_last3f", "prev_last3f_rank",
    "prev_corner4", "prev_field_size", "interval_days",
    "distance_change", "surface_change", "class_change", "venue_change",
    # 過去走からの累積と、同じレースの馬との比較
    "style_before", "course_runs_before", "course_places_before",
    "best_time_unit_rank", "best_time_dist_rank", "lead_candidates",
    # 血統
    "sire", "grandsire", "damsire",
    # 結果（特徴量にしない。行を選ぶ・目的変数・評価用の列に使う）
    "ran", "abnormal", "finish", "popularity", "win_odds", "win_payout", "place_payout",
)


class EntryRepository:
    """対象の出走の行（1行 = 1頭の出走）を読む。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """開催日・レース・馬番の順に並べる。``race_date`` は日付型にする。"""
        sql = f"""
        SELECT {", ".join(_COLUMNS)}, CAST(race_date AS DATE) AS race_date
        FROM {scope.relation}
        ORDER BY race_date, race_id, horse_no, horse_id
        """
        return self._con.execute(sql).df()
