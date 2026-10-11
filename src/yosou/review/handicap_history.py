"""過去の全出走に、レースの年ごとに「その年より前のレースだけで作った表」で不利を付ける。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.development_score import AdvantageRuns, AdvantageTableBuilder
from yosou.track_bias import DaySlopes, PriorSlopeTableBuilder, RaceSlopes, UsedSlopes
from yosou.track_bias import names as bias_names

from . import names
from .run_handicaps import COLUMNS, RunHandicaps


class HandicapHistory:
    """``ReviewRunRepository`` の出走の表から、表 G の材料（``AdvantageRuns``）とレースごとの傾き（``RaceSlopes``）を作り、
    レースの年ごとに「その年の1月1日より前のレースだけで作った表 G と過去の傾きの表」と、終わった日の全レースの傾きで、
    出走ごとの不利（``RunHandicaps``）を付ける（リークを防ぐ。学習データの材料にするときと、回顧をさかのぼって書くときの決まり）。

    ``after`` を渡すと、その日以降のレースの行だけ返す（表と傾きは全部の出走から作る）。
    """

    def __init__(self) -> None:
        self._advantage = AdvantageRuns()
        self._slopes = RaceSlopes()
        self._table_builder = AdvantageTableBuilder()
        self._prior_builder = PriorSlopeTableBuilder()
        self._day = DaySlopes()
        self._used = UsedSlopes()
        self._handicaps = RunHandicaps()

    def of(self, runs: pd.DataFrame, after: date | None = None) -> pd.DataFrame:
        """1行 = 1頭（``RunHandicaps.COLUMNS``）。開催日・レースID・馬ID の順。"""
        prepared = self._advantage.build(runs)
        slopes = self._slopes.of(runs)
        day = self._day.of_finished_day(slopes, slopes)
        targets = prepared if after is None else prepared[prepared["race_date"] >= pd.Timestamp(after)]
        parts = []
        for year, rows in targets.groupby(targets["race_date"].dt.year, sort=True):
            before = date(int(year), 1, 1)
            table = self._table_builder.build(prepared, before=before)
            prior = self._prior_builder.build(slopes, before=before)
            races = slopes[slopes[bias_names.RACE_DATE].dt.year == int(year)]
            used = self._used.of(day.loc[races.index], prior.lookup(races)).set_axis(races[bias_names.RACE_ID].astype(str))
            parts.append(self._handicaps.of(rows, table, used))
        if not parts:
            return pd.DataFrame(columns=list(COLUMNS))
        return pd.concat(parts).sort_values([names.RACE_DATE, names.RACE_ID, names.HORSE_ID], kind="stable").reset_index(drop=True)
