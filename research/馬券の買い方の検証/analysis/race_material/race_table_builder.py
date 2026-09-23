"""レースの属性・荒れ具合・本命を、1行 = 1レースの表にする。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType

from .. import column_names as names
from .race_week import RaceWeek

#: 重賞のグレードコード（A G1・B G2・C G3・D 重賞）。特別（E）・リステッド（L）・障害重賞（F〜H）は含めない。
GRADED_CODES: tuple[str, ...] = ("A", "B", "C", "D")


class RaceTableBuilder:
    """レースの属性（事実表）に、荒れ具合の予測（券種ごとの中荒れ以上の確率）・本命とその危険確率・重賞か・開催週を付ける。

    対象は予測のあるレースだけ（障害レースは予測に無いので入らない）。本命は、近走と適性モデルの
    「3着以内に入る確率」が最大の馬（同点なら人気上位）。本命が人気馬でなければ危険確率は欠損。
    """

    def __init__(self, week: RaceWeek | None = None) -> None:
        self._week = week or RaceWeek()

    def build(self, runners: pd.DataFrame, upset: pd.DataFrame, race_facts: pd.DataFrame) -> pd.DataFrame:
        races = race_facts[race_facts[names.RACE_ID].isin(runners[names.RACE_ID].unique())].copy()
        races[names.RACE_DATE] = pd.to_datetime(races[names.RACE_DATE])
        races[names.IS_GRADED] = races[names.GRADE_CODE].fillna("").str.strip().isin(GRADED_CODES)
        races[names.WEEK] = self._week.keys(races[names.RACE_DATE])
        merged = races.merge(self._upset_wide(upset), on=names.RACE_ID, how="left")
        merged = merged.merge(self._favorites(runners), on=names.RACE_ID, how="left")
        return merged.sort_values([names.RACE_DATE, names.RACE_ID]).reset_index(drop=True)

    def _upset_wide(self, upset: pd.DataFrame) -> pd.DataFrame:
        """券種ごとの「中荒れ以上の確率」を横に並べる（列は ``upset_<券種の鍵>``）。"""
        wide = upset.pivot(index=names.RACE_ID_JA, columns=names.BET_JA, values=names.UPSET_OR_MORE_JA)
        wide = wide.rename(columns={bet.label: names.upset_column(bet) for bet in BetType})
        wide.columns.name = None
        return wide.reset_index().rename(columns={names.RACE_ID_JA: names.RACE_ID})

    def _favorites(self, runners: pd.DataFrame) -> pd.DataFrame:
        """レースごとの本命（確率が最大。同点は人気上位）の馬番・確率・危険確率。"""
        ordered = runners.sort_values(
            [names.RACE_ID, names.FORM_PROB, names.POPULARITY], ascending=[True, False, True], na_position="last",
        )
        top = ordered.drop_duplicates(names.RACE_ID)
        return top[[names.RACE_ID, names.HORSE_NO, names.FORM_PROB, names.DANGER_PROB]].rename(columns={
            names.HORSE_NO: names.FAVORITE_NO, names.FORM_PROB: names.FAVORITE_PROB, names.DANGER_PROB: names.FAVORITE_DANGER,
        })
