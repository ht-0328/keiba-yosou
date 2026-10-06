"""確定前の地方の2レースと速報の行を足す。"""

from __future__ import annotations

from collections.abc import Sequence

from 合成DB import local_synth, synth

from ..synthetic_season.synthetic_horse import SyntheticHorse
from .local_career_counter import LocalCareerCounter
from .local_race_plan import LOCAL_DIRT_TRACK, LocalRacePlan
from .local_season_plan import (
    ANNOUNCED_DIRT_GOING,
    CARD_RACE_ID,
    FUTURE_DAY,
    FUTURE_FIELD_SIZE,
    PLAIN_CARD_RACE_ID,
    SCRATCHED_HORSE_NO,
    VENUE_CODE,
)

#: データ区分 2 = 出馬表（地方は、レースの 2〜5日前に馬番の決まった出馬表が出る）。
_CARD_STAGE = "2"
#: 確定前のレースで、まだ決まっていない値（実DB の出馬表と同じ形）。
_UNDECIDED_RACE = {"天候コード": "0", "入線頭数": "00", "後3ハロン": "000", "後4ハロン": "000"}
_UNDECIDED_RUNNER = {"後4ハロンタイム": "000", "タイム差": "", "マイニング区分": "0"}
#: 確定前のレースは、まだ走っていないので走破タイムが無い。
_NO_TIME = 0
#: 1R の締め切り前の複勝オッズの断面（オッズ1 の親と子）。発表月日時分は、馬体重の発表のあと。
_PLACE_HEADER, _PLACE_TABLE, _PLACE_ANNOUNCED = "o1", "o1__複勝オッズ", "01111040"
#: 確定前の2レース（rid・条件）。rid の末尾2桁がレース番号。
_FUTURE_RACES: tuple[tuple[str, LocalRacePlan], ...] = (
    (CARD_RACE_ID, LocalRacePlan("01", LOCAL_DIRT_TRACK, 1600, _NO_TIME, condition_name="Ｂ２　二")),
    (PLAIN_CARD_RACE_ID, LocalRacePlan("02", LOCAL_DIRT_TRACK, 1200, _NO_TIME, condition_name="Ｃ２　一")),
)


class LocalFutureRaceRows:
    """確定前の2レース（結果・確定オッズ・馬体重は無い）と、1R の速報（馬場状態・馬体重・取消・締め切り前の複勝オッズ）の行を足す。

    締め切り前の単勝オッズは入れない。単勝オッズが DB に無いときに --odds を案内して止まることを、ほかのテストが確かめているためである。
    """

    def __init__(self, sample: synth.Sample, careers: LocalCareerCounter) -> None:
        self._sample = sample
        self._careers = careers

    def add(self, horses: Sequence[SyntheticHorse]) -> None:
        """``horses`` の先頭から、レースごとに8頭ずつ使う。"""
        race_rows = {}
        for index, (race_id, plan) in enumerate(_FUTURE_RACES):
            field = horses[index * FUTURE_FIELD_SIZE:(index + 1) * FUTURE_FIELD_SIZE]
            race_rows[race_id] = self._add_race(plan, field)
        self._add_announcements(race_rows[CARD_RACE_ID])

    def _add_race(self, plan: LocalRacePlan, field: Sequence[SyntheticHorse]) -> dict[str, str]:
        race_row = local_synth.local_race(
            FUTURE_DAY.strftime("%Y%m%d"), plan.race_no, venue=VENUE_CODE, track=plan.track_code,
            distance=str(plan.distance_m), stage=_CARD_STAGE, field_size="00", entries=f"{len(field):02d}", dirt="0",
            condition_name=plan.condition_name, **_UNDECIDED_RACE,
        )
        self._sample.ra.append(race_row)
        for number, horse in enumerate(field, start=1):
            self._add_runner(race_row, number, horse)
        return race_row

    def _add_runner(self, race_row: dict[str, str], number: int, horse: SyntheticHorse) -> None:
        counts = self._careers.counts_of(horse)
        self._sample.nd.append(local_synth.nd(race_row, horse.hid, counts, name=horse.name))
        self._sample.se.append(local_synth.local_runner(
            race_row, number, 0, 0, hid=horse.hid, name=horse.name, sex=horse.sex_code, age="05",
            odds="0000", jockey=horse.jockey, trainer=horse.trainer, weight="", change=("", ""),
            last3f="000", mining_rank=0, style="0", **_UNDECIDED_RUNNER,
        ))

    def _add_announcements(self, card_row: dict[str, str]) -> None:
        """1R の速報。前日の夕方にダートが稍重と発表され、当日の朝に重へ変わった。馬番8 は出走取消。
        当日の朝の締め切り前の複勝オッズもある（取消の馬番8 は無投票）。"""
        first_report = synth.going_report(card_row, announced="01101700", turf="0", dirt="2")
        changed_report = synth.going_report(card_row, announced="01110900", turf="0", dirt=ANNOUNCED_DIRT_GOING, change="3")
        self._sample.going.extend([first_report, changed_report])
        announced_numbers = range(1, SCRATCHED_HORSE_NO)
        weights = {number: self._announced_weight(number) for number in announced_numbers}
        parent, children = synth.weight_report(card_row, weights, announced="01111030")
        self._sample.weight.append(parent)
        self._sample.weights.extend(children)
        self._sample.scratches.append(synth.scratch_report(card_row, SCRATCHED_HORSE_NO, announced="01110800"))
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
