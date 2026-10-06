"""架空の地方の1シーズンの行の束を作る。"""

from __future__ import annotations

import random
from datetime import date, timedelta

from 合成DB import local_synth, synth

from ..synthetic_season.synthetic_horse import SyntheticHorse
from .local_career_counter import LocalCareerCounter
from .local_finished_race_rows import LocalFinishedRaceRows
from .local_future_race_rows import LocalFutureRaceRows
from .local_race_plan import LocalRacePlan
from .local_season_plan import (
    FIELD_SIZE,
    FIRST_RACE_DAY,
    FLAT_RACES,
    HORSE_COUNT,
    LAST_RACE_DAY,
    SEED,
    STAKES_RACE,
    VENUE_NAME,
)

_DAYS_PER_WEEK = 7


class LocalSeasonBuilder:
    """架空の地方の1シーズン（毎週土曜のレースと、最後に確定前の2レース）の行の束を作る。"""

    def __init__(self) -> None:
        self._rng = random.Random(SEED)
        self._sample = synth.Sample()
        self._horses = [SyntheticHorse(number, self._rng.gauss(0.0, 1.0)) for number in range(1, HORSE_COUNT + 1)]
        careers = LocalCareerCounter()
        self._finished_races = LocalFinishedRaceRows(self._rng, self._sample, careers)
        self._future_races = LocalFutureRaceRows(self._sample, careers)

    def build(self) -> synth.Sample:
        for horse in self._horses:
            self._add_horse(horse)
        for day in self._race_days():
            self._add_day(day)
        self._future_races.add(self._shuffled_horses())
        return self._sample

    def _add_horse(self, horse: SyntheticHorse) -> None:
        """競走馬マスタ地方と血統。父は6頭、父の父は3頭、母の父は5頭の中から、番号で決まる。"""
        self._sample.nu.append(local_synth.local_horse(horse.hid, horse.name, sex=horse.sex_code, trainer=horse.trainer, area=VENUE_NAME))
        self._sample.nu_pedigree.extend(local_synth.local_pedigree(
            horse.hid, sire=f"父{horse.number % 6}", grandsire=f"父父{horse.number % 3}", damsire=f"母父{horse.number % 5}",
        ))

    def _race_days(self) -> list[date]:
        """最初の開催日から最後の開催日までの、毎週土曜。"""
        week_count = (LAST_RACE_DAY - FIRST_RACE_DAY).days // _DAYS_PER_WEEK + 1
        return [FIRST_RACE_DAY + timedelta(weeks=week) for week in range(week_count)]

    def _add_day(self, day: date) -> None:
        """1日のレース。馬をくじで並べ、レースごとに10頭ずつ割り当てる。"""
        horses = self._shuffled_horses()
        for index, plan in enumerate(self._plans_on(day)):
            field = horses[index * FIELD_SIZE:(index + 1) * FIELD_SIZE]
            self._finished_races.add(day, plan, field)

    def _plans_on(self, day: date) -> list[LocalRacePlan]:
        """その日のレース。月の最初の土曜だけ、重賞を足す。"""
        is_first_saturday = day.day <= _DAYS_PER_WEEK
        return [*FLAT_RACES, STAKES_RACE] if is_first_saturday else list(FLAT_RACES)

    def _shuffled_horses(self) -> list[SyntheticHorse]:
        horses = list(self._horses)
        self._rng.shuffle(horses)
        return horses
