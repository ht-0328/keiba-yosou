"""確定前の3レースと速報の行を足す。"""

from __future__ import annotations

from collections.abc import Sequence

from 合成DB import synth

from .career_counter import CareerCounter
from .race_plan import JUMP_TRACK, TURF_TRACK, RacePlan
from .season_plan import (
    ANNOUNCED_TURF_GOING,
    CARD_RACE_ID,
    ENTRY_LIST_RACE_ID,
    FUTURE_DAY,
    FUTURE_FIELD_SIZE,
    JUMP_CARD_RACE_ID,
    JUMP_RACE,
    SCRATCHED_HORSE_NO,
    VENUE_CODE,
)
from .synthetic_horse import SyntheticHorse
from .workout_log import WorkoutLog

#: データ区分。1 = 出走馬名表（木曜。枠番・馬番が未定）、2 = 出馬表（金・土）。
_ENTRY_LIST_STAGE, _CARD_STAGE = "1", "2"
#: 確定前のレースで、まだ決まっていない値（実DB の出走馬名表・出馬表と同じ形）。
_UNDECIDED_RACE = {"天候コード": "0", "入線頭数": "00", "後3ハロン": "000", "後4ハロン": "000"}
_UNDECIDED_RUNNER = {"後4ハロンタイム": "000", "タイム差": "", "マイニング区分": "0"}
_UNDECIDED_NUMBERS = {"枠番": "0", "馬番": "00"}
#: 確定前のレースは、まだ走っていないので走破タイムが無い。
_NO_TIME = 0
#: 1R の締め切り前の複勝オッズの断面（オッズ1 の親と子）。発表月日時分は、馬体重の発表のあと。
_PLACE_HEADER, _PLACE_TABLE, _PLACE_ANNOUNCED = "o1", "o1__複勝オッズ", "01111040"
#: 確定前の3レース（rid・条件・データ区分）。rid の末尾2桁がレース番号。
_FUTURE_RACES: tuple[tuple[str, RacePlan, str], ...] = (
    (CARD_RACE_ID, RacePlan("01", TURF_TRACK, 1600, _NO_TIME), _CARD_STAGE),
    (ENTRY_LIST_RACE_ID, RacePlan("02", TURF_TRACK, 2000, _NO_TIME), _ENTRY_LIST_STAGE),
    (JUMP_CARD_RACE_ID, RacePlan("03", JUMP_TRACK, JUMP_RACE.distance_m, _NO_TIME), _CARD_STAGE),
)


class FutureRaceRows:
    """確定前の3レース（結果・確定オッズ・馬体重は無い）と、1R の速報（馬場状態・馬体重・取消・締め切り前の複勝オッズ）の行を足す。

    締め切り前の単勝オッズは入れない。単勝オッズが DB に無いときに --odds・--pops を案内して止まることを、
    ほかのテストが確かめているためである（テストは単勝オッズと人気を引数で渡す）。複勝オッズには引数が無いので、DB に入れておく。
    """

    def __init__(self, sample: synth.Sample, careers: CareerCounter, workouts: WorkoutLog) -> None:
        self._sample = sample
        self._careers = careers
        self._workouts = workouts

    def add(self, horses: Sequence[SyntheticHorse]) -> None:
        """``horses`` の先頭から、レースごとに8頭ずつ使う。"""
        race_rows = {}
        for index, (race_id, plan, stage) in enumerate(_FUTURE_RACES):
            field = horses[index * FUTURE_FIELD_SIZE:(index + 1) * FUTURE_FIELD_SIZE]
            race_rows[race_id] = self._add_race(plan, stage, field)
        self._add_announcements(race_rows[CARD_RACE_ID])

    def _add_race(self, plan: RacePlan, stage: str, field: Sequence[SyntheticHorse]) -> dict[str, str]:
        race_row = synth.race(
            FUTURE_DAY.strftime("%Y%m%d"), plan.race_no, venue=VENUE_CODE, track=plan.track_code,
            distance=str(plan.distance_m), stage=stage, field_size="00",
            entries=f"{len(field):02d}", turf="0", dirt="0", **_UNDECIDED_RACE,
        )
        self._sample.ra.append(race_row)
        for number, horse in enumerate(field, start=1):
            self._add_runner(race_row, number, horse)
        return race_row

    def _add_runner(self, race_row: dict[str, str], number: int, horse: SyntheticHorse) -> None:
        is_numbered = race_row["データ区分"] == _CARD_STAGE
        undecided = _UNDECIDED_RUNNER if is_numbered else {**_UNDECIDED_RUNNER, **_UNDECIDED_NUMBERS}
        self._workouts.add_before(horse, FUTURE_DAY)
        counts = self._careers.counts_of(horse)
        self._sample.ck.append(synth.ck(race_row, horse.hid, counts, name=horse.name))
        self._sample.se.append(synth.runner(
            race_row, number, 0, 0, hid=horse.hid, name=horse.name, sex=horse.sex_code, age="05",
            odds="0000", jockey=horse.jockey, trainer=horse.trainer, weight="", change=("", ""),
            last3f="000", mining_rank=0, style="0", **undecided,
        ))

    def _add_announcements(self, card_row: dict[str, str]) -> None:
        """1R の速報。前日の夕方に芝が稍重と発表され、当日の朝に重へ変わった。馬番8 は出走取消。
        当日の朝の締め切り前の複勝オッズもある（取消の馬番8 は無投票）。"""
        first_report = synth.going_report(card_row, announced="01101700", turf="2", dirt="1")
        changed_report = synth.going_report(
            card_row, announced="01110900", turf=ANNOUNCED_TURF_GOING, dirt="0", change="3",
        )
        self._sample.going.extend([first_report, changed_report])
        announced_numbers = range(1, SCRATCHED_HORSE_NO)
        weights = {number: self._announced_weight(number) for number in announced_numbers}
        parent, children = synth.weight_report(card_row, weights, announced="01111030")
        self._sample.weight.append(parent)
        self._sample.weights.extend(children)
        self._sample.scratches.append(
            synth.scratch_report(card_row, SCRATCHED_HORSE_NO, announced="01110800"))
        self._add_place_odds(card_row)

    def _add_place_odds(self, card_row: dict[str, str]) -> None:
        """1R の締め切り前の複勝オッズ（データ区分 1 の断面）。馬番が大きいほど高い。取消の馬番は無投票（0）。"""
        header = synth.odds_header(card_row, _PLACE_HEADER, stage="1", announced=_PLACE_ANNOUNCED)
        self._sample.odds.append((_PLACE_HEADER, header))
        for number in range(1, FUTURE_FIELD_SIZE + 1):
            low = 0 if number == SCRATCHED_HORSE_NO else 11 + 6 * number
            row = synth.range_odds_row(card_row, _PLACE_TABLE, f"{number:02d}", low, 2 * low, seq=number,
                                       announced=_PLACE_ANNOUNCED)
            self._sample.odds.append((_PLACE_TABLE, row))

    def _announced_weight(self, number: int) -> tuple[str, str, str]:
        """（馬体重, 増減符号, 増減差）。馬番が奇数なら減、偶数なら増。増減差は馬番と同じ kg。"""
        sign = "-" if number % 2 else "+"
        return f"{470 + number}", sign, f"{number:03d}"
