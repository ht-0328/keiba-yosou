"""馬の力の材料（まとまり M）の表を作る。"""

from __future__ import annotations

import pandas as pd

from .ability_columns import RECORD_GROUPS, ability_columns
from .ability_sources import AbilitySources
from .cumulative_record_rates import CumulativeRecordRates
from .past_run_history import PastRunHistory
from .race_level_columns import RaceLevelColumns
from .race_pace import RacePace
from .race_relative_columns import RaceRelativeColumns
from .race_strength import RaceStrength
from .recent_people_rates import RecentPeopleRates
from .sale_price_columns import SalePriceColumns
from .speed_figure_history import SpeedFigureHistory

#: 行を突き合わせる鍵（木曜は馬番が無いので、馬で突き合わせる）。
KEY = ["race_id", "horse_id"]
#: スピード指数の表に要る、走ごとの列。
_FIGURE_RUN_COLUMNS = ["race_id", "race_date", "horse_id", "venue_code", "surface", "distance_m", "condition", "finish"]
#: 数にそろえる列（成績を数える・過去走を作るのに使う）。
_NUMERIC = ["finish", "distance_m", "field_size", "frame_no", "horse_no"]


class AbilityTableBuilder:
    """元の記録（``AbilitySources``）から、対象の出走（``is_target``）ごとの馬の力の材料の表を作る。部品を順に呼ぶだけ。

    研究「馬の力と展開でオッズに勝つ」の学習用の表の作り方（``research/馬の力と展開でオッズに勝つ/analysis/dataset_builder.py``）を、
    まだ走っていないレースにも付けられるように、馬で突き合わせる形にしたもの。どの列も、そのレースより前の記録だけから作る。
    列は race_id・horse_id と ``ability_columns()``（202個。どれも小数）。
    """

    def build(self, sources: AbilitySources) -> pd.DataFrame:
        runs = self._ran(sources.runs)
        figures = SpeedFigureHistory().build(self._figure_runs(runs, sources.figures))
        past = PastRunHistory().build(runs, RaceStrength().of(runs, figures), RacePace().of(runs))
        table = runs[runs["is_target"]].merge(figures, on=KEY, how="left").merge(past, on=KEY, how="left")
        table = table.merge(sources.workouts, on=KEY, how="left")
        for name, keys in RECORD_GROUPS.items():
            table = table.merge(CumulativeRecordRates().build(runs, keys, name), on=KEY, how="left")
        table = table.merge(RecentPeopleRates().build(runs, table), on=KEY, how="left")
        added = [RaceRelativeColumns().build(table), RaceLevelColumns().build(table),
                 SalePriceColumns().build(table, sources.sales)]
        table = pd.concat([table, *added], axis=1)
        columns = list(ability_columns())
        values = table[columns].apply(lambda column: pd.to_numeric(column, errors="coerce")).astype("float64")
        return pd.concat([table[KEY], values], axis=1)

    def _ran(self, runs: pd.DataFrame) -> pd.DataFrame:
        """出走した行（対象の出走は、取消の分かっていない行も含める）。数の列は小数にそろえる。"""
        numeric = runs[_NUMERIC].apply(lambda column: pd.to_numeric(column, errors="coerce")).astype(float)
        typed = runs.assign(**{column: numeric[column] for column in _NUMERIC},
                            race_date=pd.to_datetime(runs["race_date"]),
                            ran=runs["ran"].astype("boolean").fillna(runs["is_target"]).astype(bool))
        return typed[typed["ran"]].reset_index(drop=True)

    def _figure_runs(self, runs: pd.DataFrame, figures: pd.DataFrame) -> pd.DataFrame:
        """出走した行に、その走のスピード指数（``figure``。まだ走っていないレースは欠損値）を付ける。"""
        known = figures[[*KEY, "figure"]].drop_duplicates(KEY)
        return runs[_FIGURE_RUN_COLUMNS].merge(known, on=KEY, how="left")
