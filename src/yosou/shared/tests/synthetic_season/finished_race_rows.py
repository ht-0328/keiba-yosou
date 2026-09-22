"""終わった1レースの行を足す。"""

from __future__ import annotations

import random
from collections.abc import Sequence
from datetime import date

from 合成DB import synth

from .career_counter import CareerCounter
from .finished_race import FinishedRace
from .race_outcome import RaceOutcome
from .race_plan import RacePlan
from .season_plan import FIELD_SIZE, VENUE_CODE
from .synthetic_horse import SyntheticHorse
from .workout_log import WorkoutLog

#: 馬場状態コードのくじ。良（1）が出やすい。
_GOING_DRAWS = "1112223334"
#: 馬場状態が無い側（芝のレースのダート、ダートのレースの芝）に入れる値。
_NO_GOING = "0"
#: 脚質は、着順の3つごとに 逃げ（1）・先行（2）・差し（3）・追込（4）。
_FINISHES_PER_STYLE, _LAST_STYLE = 3, 4


class FinishedRaceRows:
    """終わった1レースの、レース・出走・出走別着度数・調教の行を、合成DB の行の束に足す。"""

    def __init__(self, rng: random.Random, sample: synth.Sample, careers: CareerCounter,
                 workouts: WorkoutLog) -> None:
        self._rng = rng
        self._sample = sample
        self._careers = careers
        self._workouts = workouts

    def add(self, day: date, plan: RacePlan, field: Sequence[SyntheticHorse]) -> None:
        going_code = self._rng.choice(_GOING_DRAWS)
        race = FinishedRace(plan, self._race_row(day, plan, going_code), RaceOutcome(self._rng, field))
        self._sample.ra.append(race.row)
        for horse in field:
            self._workouts.add_before(horse, day)
        for number, horse in enumerate(field, start=1):
            self._add_runner(race, number, horse)
        self._careers.record_race(plan, going_code, field, race.outcome)

    def _race_row(self, day: date, plan: RacePlan, going_code: str) -> dict[str, str]:
        return synth.race(
            day.strftime("%Y%m%d"), plan.race_no, venue=VENUE_CODE, track=plan.track_code,
            distance=str(plan.distance_m),
            turf=_NO_GOING if plan.is_dirt else going_code,
            dirt=going_code if plan.is_dirt else _NO_GOING,
            field_size=f"{FIELD_SIZE:02d}", entries=f"{FIELD_SIZE:02d}",
        )

    def _add_runner(self, race: FinishedRace, number: int, horse: SyntheticHorse) -> None:
        """1頭の、出走別着度数（このレースの前の時点の着回数）と、出走の行。"""
        counts = self._careers.counts_of(horse)
        self._sample.ck.append(synth.ck(race.row, horse.hid, counts, name=horse.name))
        self._sample.se.append(self._runner_row(race, number, horse))

    def _runner_row(self, race: FinishedRace, number: int, horse: SyntheticHorse) -> dict[str, str]:
        finish = race.outcome.finish_of(horse)
        popularity = race.outcome.popularity_of(horse)
        return synth.runner(
            race.row, number, popularity, finish,
            hid=horse.hid, name=horse.name, sex=horse.sex_code, age="04",
            abnormal=race.outcome.abnormal_code(horse),
            odds=f"{15 + 20 * popularity:04d}" if popularity else "0000",
            jockey=horse.jockey, trainer=horse.trainer,
            time=str(race.plan.base_time + 2 * max(finish - 1, 0)),
            last3f=f"{340 + 3 * finish:03d}",
            style=self._style_code(finish),
            weight=f"{450 + horse.number % 40}", change=("+", "002"),
        )

    def _style_code(self, finish: int) -> str:
        """脚質。上位の馬ほど前で走ったことにする。着順が無ければ 0（判定なし）。"""
        if not finish:
            return "0"
        return str(min(_LAST_STYLE, 1 + (finish - 1) // _FINISHES_PER_STYLE))
