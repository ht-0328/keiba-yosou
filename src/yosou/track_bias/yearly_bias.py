"""過去の出走に、その年より前のレースだけで作った過去の傾きの表と、終わったレースの傾きから、バイアスの補正を付ける。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.feature import PredictionTiming

from . import names
from .bias_correction import COLUMNS, BiasCorrection
from .day_slopes import DaySlopes
from .prior_slope_table_builder import PriorSlopeTableBuilder
from .used_slopes import UsedSlopes

#: 予測の表（展開の予想④）の鍵。
_KEY: list[str] = ["race_id", "horse_id"]


class YearlyBias:
    """予測の表（1行 = 1頭。``race_id``・``horse_id`` と展開の予想④ ``corner4_pred``）に、レースの年ごとに「その年の1月1日より前の
    レースだけで作った過去の傾きの表」と、そのレースより前に終わったレースの傾き（当日の先のレース・前の日のレース。``DaySlopes``）で
    バイアスの補正を付ける（リークを防ぐ。学習データの材料にするときの決まり）。

    ``runs`` は ``BiasRunRepository`` の表（出走の馬番・頭数と、レースの鍵）、``slopes`` は ``RaceSlopes`` の表（レースごとの傾き）。
    材料に無いレース（障害・まだ走っていないレースなど）の行は欠損値。
    """

    def __init__(self) -> None:
        self._builder = PriorSlopeTableBuilder()
        self._day = DaySlopes()
        self._used = UsedSlopes()
        self._correction = BiasCorrection()

    def of(self, forecasts: pd.DataFrame, runs: pd.DataFrame, slopes: pd.DataFrame, timing: PredictionTiming) -> pd.DataFrame:
        """列は ``BiasCorrection.COLUMNS`` と ``race_date``。行の並びと index は ``forecasts`` と同じ。"""
        keyed = forecasts[[*_KEY, "corner4_pred"]].astype({key: str for key in _KEY})
        entries = keyed.merge(runs[[*_KEY, "horse_no", "field_size"]].astype({key: str for key in _KEY}), on=_KEY, how="left")
        entries = entries.set_axis(forecasts.index)
        races = slopes.set_index(names.RACE_ID)
        race_rows = races.reindex(entries[names.RACE_ID])
        race_date = pd.Series(race_rows[names.RACE_DATE].to_numpy(), index=forecasts.index)
        used = self._used_by_race(slopes, race_rows.index.unique(), timing)
        corrected = self._correction.of(entries, used)
        return corrected.reindex(columns=list(COLUMNS)).assign(race_date=race_date)

    def _used_by_race(self, slopes: pd.DataFrame, race_ids: pd.Index, timing: PredictionTiming) -> pd.DataFrame:
        """対象のレース（``race_ids``）ごとの使う傾き（index は race_id）。過去の傾きの表は年ごとに作り直す。"""
        targets = slopes[slopes[names.RACE_ID].isin(race_ids)].reset_index(drop=True)
        if targets.empty:
            return pd.DataFrame(columns=[names.USED_INNER, names.USED_FRONT])
        day = self._day.of(targets, slopes, timing)
        parts = []
        for year, rows in targets.groupby(targets[names.RACE_DATE].dt.year, sort=True):
            table = self._builder.build(slopes, before=date(int(year), 1, 1))
            parts.append(self._used.of(day.loc[rows.index], table.lookup(rows)))
        used = pd.concat(parts)
        return used.set_axis(targets.loc[used.index, names.RACE_ID].astype(str))
