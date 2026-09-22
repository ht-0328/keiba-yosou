"""調教の行を作る。"""

from __future__ import annotations

import random
from datetime import date, timedelta

from 合成DB import synth

from .synthetic_horse import SyntheticHorse

#: 開催日の何日前に調教するか。
_DAYS_BEFORE_RACE: tuple[int, ...] = (3, 10)
#: 能力が 0 の馬の、4ハロンとラスト1ハロンのタイム（秒）と、能力 1 あたりに速くなる秒数。
_BASE_FOUR_FURLONGS, _FOUR_FURLONGS_PER_ABILITY = 54.0, 0.8
_BASE_LAST_FURLONG, _LAST_FURLONG_PER_ABILITY = 12.8, 0.3


class WorkoutLog:
    """開催日の3日前と10日前の調教の行を、合成DB の行の束に足す。能力が高い馬ほどタイムが速い。"""

    def __init__(self, rng: random.Random, sample: synth.Sample) -> None:
        self._rng = rng
        self._sample = sample
        self._logged: set[tuple[str, date]] = set()

    def add_before(self, horse: SyntheticHorse, race_day: date) -> None:
        for days_before in _DAYS_BEFORE_RACE:
            self._add(horse, race_day - timedelta(days=days_before))

    def _add(self, horse: SyntheticHorse, work_day: date) -> None:
        """調教1本。同じ馬の同じ日の調教は1本だけ。"""
        if (horse.hid, work_day) in self._logged:
            return
        self._logged.add((horse.hid, work_day))
        four_furlongs = _BASE_FOUR_FURLONGS - _FOUR_FURLONGS_PER_ABILITY * horse.ability
        last_furlong = _BASE_LAST_FURLONG - _LAST_FURLONG_PER_ABILITY * horse.ability
        times = {
            "four_furlongs": f"{round((four_furlongs + self._rng.gauss(0.0, 0.5)) * 10):04d}",
            "last_furlong": f"{round((last_furlong + self._rng.gauss(0.0, 0.2)) * 10):03d}",
        }
        self._append(horse, work_day.strftime("%Y%m%d"), times)

    def _append(self, horse: SyntheticHorse, day: str, times: dict[str, str]) -> None:
        if horse.trains_on_wood:
            self._sample.wood.append(synth.wood_workout(horse.hid, day, **times))
            return
        self._sample.hill.append(synth.hill_workout(horse.hid, day, **times))
