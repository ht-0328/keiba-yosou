"""過去走を、馬ごとの「その走までの近5走の人気のまとめ」にする。"""

from __future__ import annotations

import pandas as pd

from ..value_types import as_numbers

#: 近走として数える走数（まとまり E と同じ数え方）。
RECENT_RUNS = 5
#: まとめの列の名前（そのまま特徴量の名前になる）。
WORSE_THAN_POPULARITY = "近5走で人気より悪い着順だった回数"
AVERAGE_POPULARITY = "近5走の平均人気"
SUMMARY_COLUMNS: tuple[str, ...] = (WORSE_THAN_POPULARITY, AVERAGE_POPULARITY)

#: 途中の計算に使う列の名前。
_WORSE, _POPULARITY = "worse", "popularity"


class PopularityRunSummary:
    """過去走の表（1行 = 1走）に、その走を含めた新しい5走の人気のまとめを付ける（まとまり J の材料）。

    5走に満たなければ、ある分だけで計算する。着順か人気の無い走（競走中止・人気の無いレースなど）は、
    回数にも平均にも数えない。
    """

    def build(self, past_runs: pd.DataFrame) -> pd.DataFrame:
        """列は ``horse_id``・``race_date`` と ``SUMMARY_COLUMNS``。馬・開催日の古い順に並べる。"""
        runs = past_runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        runs = runs.reset_index(drop=True)
        horse = runs["horse_id"]
        measures = self._measures(runs)
        recent = measures.groupby(horse, sort=False).rolling(RECENT_RUNS, min_periods=1)
        return pd.DataFrame({
            "horse_id": horse,
            "race_date": runs["race_date"],
            WORSE_THAN_POPULARITY: self._flattened(recent[_WORSE].sum()),
            AVERAGE_POPULARITY: self._flattened(recent[_POPULARITY].mean()),
        })

    def _measures(self, runs: pd.DataFrame) -> pd.DataFrame:
        """数える値。着順か人気の無い走は、どちらも欠損値にして数から外す。"""
        finish = as_numbers(runs["finish"])
        popularity = as_numbers(runs["popularity"])
        counted = finish.notna() & popularity.notna()
        return pd.DataFrame({
            _WORSE: (finish > popularity).astype("float64").where(counted),
            _POPULARITY: popularity.where(counted),
        })

    def _flattened(self, rolled: pd.Series) -> pd.Series:
        """馬ごとの窓の結果から、馬の段の index を外して、過去走と同じ並びに戻す。"""
        return rolled.reset_index(level=0, drop=True)
