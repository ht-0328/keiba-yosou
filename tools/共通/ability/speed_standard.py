"""コースの基準タイム・レースの水準の差・その日の馬場差を、過去のレースから求める。"""

from __future__ import annotations

import pandas as pd

from .race_table import FIELD_LEVEL, MEDIAN_LOG_TIME
from .standard_table import COURSE_KEY, DAY_KEY, REFERENCE_LEVEL, StandardTable

#: くり返しの回数（20回で、どの値も 0.001% より小さくしか動かなくなる）。
_ROUNDS = 20


class SpeedStandard:
    """1行 = 1レースの表（``RaceTable``）の、中央値タイムの対数を3つに分ける。

    中央値タイムの対数 = コースの基準 + レースの水準の差 + その日の馬場差 + 残り

    - コースの基準: 競馬場・トラック・距離ごと。基準の水準（1勝クラス・古馬）の、ふつうの馬場でのタイム。
    - レースの水準の差: クラスと年齢の組ごと。1勝クラス・古馬を 0 として、何%速いか遅いか（強いレースほどマイナス）。
    - その日の馬場差: 開催日・競馬場・芝ダごと。その日の馬場が、ふつうより何%速かったか遅かったか。
    3つを順に「ほかの2つを引いた残りの平均」で求め直すことを、くり返す。例: ある日の東京の芝の全レースが、
    コースの基準と水準の差から見込むより 0.5% 速ければ、その日の馬場差は −0.5。
    ``until`` までのレースだけで求める（あとの年を当てるときに、先の年のタイムを混ぜないため）。
    """

    def fit(self, races: pd.DataFrame, until: pd.Timestamp) -> StandardTable:
        data = races[(pd.to_datetime(races["race_date"]) <= until) & races[MEDIAN_LOG_TIME].notna()]
        y = data[MEDIAN_LOG_TIME]
        course_keys = [data[key] for key in COURSE_KEY]
        day_keys = [data[key] for key in DAY_KEY]
        level = pd.Series(0.0, index=data.index)
        day = pd.Series(0.0, index=data.index)
        for _ in range(_ROUNDS):
            course = (y - level - day).groupby(course_keys).transform("mean")
            level = (y - course - day).groupby(data[FIELD_LEVEL]).transform("mean")
            level = level - level[data[FIELD_LEVEL] == REFERENCE_LEVEL].mean()
            day = (y - course - level).groupby(day_keys).transform("mean")
        shift = day.mean()
        course_table = (course + shift).groupby(course_keys).first()
        level_table = level.groupby(data[FIELD_LEVEL]).first()
        return StandardTable(course_table, level_table)
