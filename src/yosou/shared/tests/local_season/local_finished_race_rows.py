"""終わった地方の1レースの行を足す。"""

from __future__ import annotations

import random
from collections.abc import Sequence
from datetime import date

from 合成DB import local_synth, synth

from ..synthetic_season.finished_race import FinishedRace
from ..synthetic_season.payout_rows import PayoutRows
from ..synthetic_season.race_outcome import RaceOutcome
from ..synthetic_season.synthetic_horse import SyntheticHorse
from .local_career_counter import LocalCareerCounter
from .local_race_plan import LocalRacePlan
from .local_season_plan import FIELD_SIZE, VENUE_CODE

#: 馬場状態コードのくじ。良（1）が出やすい。
_GOING_DRAWS = "1112223334"
#: 脚質は、着順の3つごとに 逃げ（1）・先行（2）・差し（3）・追込（4）。
_FINISHES_PER_STYLE, _LAST_STYLE = 3, 4


class LocalFinishedRaceRows:
    """終わった地方の1レースの、レース・出走・出走別着度数地方の行を、合成DB の行の束に足す。"""

    def __init__(self, rng: random.Random, sample: synth.Sample, careers: LocalCareerCounter) -> None:
        self._rng = rng
        self._sample = sample
        self._careers = careers
        self._payouts = PayoutRows(sample)

    def add(self, day: date, plan: LocalRacePlan, field: Sequence[SyntheticHorse]) -> None:
        going_code = self._rng.choice(_GOING_DRAWS)
        race = FinishedRace(plan, self._race_row(day, plan, going_code), RaceOutcome(self._rng, field))
        self._sample.ra.append(race.row)
        for number, horse in enumerate(field, start=1):
            self._add_runner(race, number, horse)
        self._payouts.add(race.row, {
            number: (race.outcome.finish_of(horse), race.outcome.popularity_of(horse))
            for number, horse in enumerate(field, start=1)
        })
        self._careers.record_race(plan, going_code, field, race.outcome)

    def _race_row(self, day: date, plan: LocalRacePlan, going_code: str) -> dict[str, str]:
        return local_synth.local_race(
            day.strftime("%Y%m%d"), plan.race_no, venue=VENUE_CODE, track=plan.track_code, distance=str(plan.distance_m),
            dirt=going_code, field_size=f"{FIELD_SIZE:02d}", entries=f"{FIELD_SIZE:02d}",
            condition_name=plan.condition_name, name=plan.name, grade=plan.grade, stakes_no=plan.stakes_no,
        )

    def _add_runner(self, race: FinishedRace, number: int, horse: SyntheticHorse) -> None:
        """1頭の、出走別着度数地方（このレースの前の時点の着回数）と、出走の行。"""
        counts = self._careers.counts_of(horse)
        self._sample.nd.append(local_synth.nd(race.row, horse.hid, counts, name=horse.name))
        self._sample.se.append(self._runner_row(race, number, horse))

    def _runner_row(self, race: FinishedRace, number: int, horse: SyntheticHorse) -> dict[str, str]:
        finish = race.outcome.finish_of(horse)
        popularity = race.outcome.popularity_of(horse)
        return local_synth.local_runner(
            race.row, number, popularity, finish,
            hid=horse.hid, name=horse.name, sex=horse.sex_code, age="04",
            abnormal=race.outcome.abnormal_code(horse),
            odds=f"{15 + 20 * popularity:04d}" if popularity else "0000",
            jockey=horse.jockey, trainer=horse.trainer,
            time=str(race.plan.base_time + 2 * max(finish - 1, 0)),
            last3f=f"{370 + 3 * finish:03d}",
            style=self._style_code(finish),
            weight=f"{450 + horse.number % 40}", change=("+", "002"),
        )

    def _style_code(self, finish: int) -> str:
        """脚質。上位の馬ほど前で走ったことにする。着順が無ければ 0（判定なし）。"""
        if not finish:
            return "0"
        return str(min(_LAST_STYLE, 1 + (finish - 1) // _FINISHES_PER_STYLE))
