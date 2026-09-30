"""出走の表から、スピード指数と能力指数を作るまでをつなぐ。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .ability_index import AbilityIndex
from .ability_settings import AbilitySettings
from .first_conditions import FirstConditions
from .pace_adjustment import PaceAdjustment
from .pace_balance import PACE, PaceBalance
from .pedigree_aptitude import PedigreeAptitude
from .race_table import RaceTable
from .speed_figure import SpeedFigure
from .speed_standard import SpeedStandard
from .standard_table import COURSE_STANDARD, LEVEL_GAP, TRACK_VARIANT


@dataclass(frozen=True)
class AbilityResult:
    """作った結果。``runs`` は出走の表にスピード指数と能力指数の列を足したもの。``races`` は1行 = 1レースの表
    （コースの基準・水準の差・馬場差・ペース）。``pace_offsets`` はペース補正の表（補正しないなら空）。
    """

    runs: pd.DataFrame
    races: pd.DataFrame
    pace_offsets: pd.Series


class AbilityBuilder:
    """出走の表（``RunSource`` が読んだもの。これから走るレースの行を足してもよい）から、指数を作る。

    1. レースの表を作り、``until`` までのレースでコースの基準・水準の差を求め、全部のレースに馬場差を付ける。
    2. ``until`` までのレースで、ペースの基準を作り、全部のレースにペースを付ける。
    3. 斤量補正だけのスピード指数を作り、``until`` までの走でペース補正の大きさを測って、指数を作り直す。
    4. 能力指数を作る。
    5. 設定で親（``pedigree``）を選んでいれば、初めての条件の適性を血統で補う（``PedigreeAptitude``）。

    ``race_table`` は、レースの表の作り方を変えて比べるとき（研究）に渡す。
    """

    def __init__(self, settings: AbilitySettings, until: pd.Timestamp, race_table: RaceTable | None = None) -> None:
        self._settings = settings
        self._until = until
        self._race_table = race_table or RaceTable()

    def build(self, runs: pd.DataFrame) -> AbilityResult:
        races = self._race_table.build(runs)
        races = SpeedStandard().fit(races, self._until).apply(races)
        fitted = pd.to_datetime(races["race_date"]) <= self._until
        races = races.assign(**{PACE: PaceBalance().fit(races[fitted]).band(races)})
        joined = runs.merge(races[["race_id", COURSE_STANDARD, LEVEL_GAP, TRACK_VARIANT, PACE]], on="race_id", how="left")
        joined.index = runs.index
        offsets = self._pace_offsets(joined)
        figured = self._figure(offsets if self._settings.pace else None).build(joined)
        return AbilityResult(self._pedigree(AbilityIndex(self._settings).build(figured)), races, offsets)

    def _pedigree(self, runs: pd.DataFrame) -> pd.DataFrame:
        if not self._settings.pedigree:
            return runs
        flagged = FirstConditions(self._settings).build(runs)
        return PedigreeAptitude(self._settings).fit(flagged).fill(flagged)

    def _pace_offsets(self, runs: pd.DataFrame) -> pd.Series:
        if not self._settings.pace:
            return pd.Series(dtype=float)
        plain = self._figure(None).build(runs)
        return PaceAdjustment().fit(plain[plain["race_date"] <= self._until])

    def _figure(self, offsets: pd.Series | None) -> SpeedFigure:
        s = self._settings
        return SpeedFigure(s.weight_per_kg, offsets, track_variant=s.track_variant, floor_gap=s.floor_gap)
