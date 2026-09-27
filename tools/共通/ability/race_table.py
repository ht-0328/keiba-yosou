"""出走の表から、基準タイムを求めるための1行 = 1レースの表を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 出力の列。
MEDIAN_LOG_TIME = "中央値タイムの対数"
FIELD_LEVEL = "レースの水準"
#: 1行 = 1レースで持つ列。
_RACE_COLUMNS: tuple[str, ...] = (
    "race_id", "race_date", "venue_code", "track_code", "surface", "distance_m", "condition", "class_name",
    "first3f", "last3f_race",
)


class RaceTable:
    """出走の表を、1行 = 1レースにまとめる。

    - 中央値タイムの対数: 着順の付いた馬の走破タイムの中央値の、自然対数 × 100。対数にするのは、距離の違う
      レースを「何%速いか」でそろえて比べるため（例: 96.0秒と 95.0秒の差は、およそ 1.04%）。
    - レースの水準: クラスと年齢の組（例: 「1勝クラス・古馬」「未勝利・2歳」）。出走馬の強さの目安で、
      基準タイムを求めるときに、強いレースの多い日を「速い馬場」と見誤らないために使う。
      年齢は出走馬のいちばん若い馬齢で、2歳・3歳（3歳だけのレース）・古馬（4歳以上か、3歳以上の混合）に分ける。
    """

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        timed = runs[runs["finish"].notna() & (runs["finish_time"] > 0)]
        median = timed.groupby("race_id")["finish_time"].median()
        ages = runs.groupby("race_id")["age"].agg(["min", "max"])
        races = runs.drop_duplicates("race_id")[list(_RACE_COLUMNS)].set_index("race_id")
        age_group = np.select([ages["min"] <= 2, (ages["min"] == 3) & (ages["max"] == 3)], ["2歳", "3歳"], default="古馬")
        level = races["class_name"].astype(str) + "・" + pd.Series(age_group, index=ages.index).reindex(races.index)
        return races.assign(**{MEDIAN_LOG_TIME: 100 * np.log(median.reindex(races.index)), FIELD_LEVEL: level}).reset_index()
