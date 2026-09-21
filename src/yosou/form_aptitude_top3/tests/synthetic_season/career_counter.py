"""馬ごとの通算の着回数を数える。"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from 合成DB import synth

from .race_outcome import RaceOutcome
from .race_plan import RacePlan
from .season_plan import VENUE_NAME
from .synthetic_horse import SyntheticHorse

_TOTAL_ITEM = "中央合計着回数"
#: 馬場状態コード → 出走別着度数の欄の名前での書き方。
_GOING_NAMES = {"1": "良", "2": "稍", "3": "重", "4": "不"}
#: 着回数の6つの列のうち、着外（6着以下と、着順なし）を入れる位置。
_OUT_OF_PLACE_SLOT = synth.CK_SLOTS - 1
#: 距離帯は 1001m から 200m 刻み（このシーズンの平地は 1400〜2000m だけ）。
_BAND_START_M, _BAND_STEP_M = 1001, 200


class CareerCounter:
    """馬ごとに、出走別着度数の欄ごとの着回数（1着〜5着と着外）を、シーズンの初めから数える。"""

    def __init__(self) -> None:
        self._counts: dict[str, dict[str, list[int]]] = defaultdict(self._empty_items)

    def counts_of(self, horse: SyntheticHorse) -> dict[str, list[int]]:
        """その馬の、いまの時点の着回数（欄の名前 → 6つの回数）。"""
        return self._counts[horse.hid]

    def record_race(self, plan: RacePlan, going_code: str, field: Sequence[SyntheticHorse],
                    outcome: RaceOutcome) -> None:
        """1レースの結果を、出走した馬の着回数に足す。"""
        items = self._items(plan, going_code)
        for horse in field:
            self._record(horse, outcome, items)

    def _record(self, horse: SyntheticHorse, outcome: RaceOutcome, items: Sequence[str]) -> None:
        if not outcome.has_run(horse):
            return
        slot = self._slot(outcome.finish_of(horse))
        for item in items:
            self._counts[horse.hid][item][slot] += 1

    def _slot(self, finish: int) -> int:
        """着順を入れる位置。1〜5着はその着順の位置、6着以下と着順なし（競走中止）は着外の位置。"""
        is_in_top5 = 1 <= finish <= _OUT_OF_PLACE_SLOT
        return finish - 1 if is_in_top5 else _OUT_OF_PLACE_SLOT

    def _items(self, plan: RacePlan, going_code: str) -> list[str]:
        """そのレースの結果を足す欄。障害は、中央の合計だけ。"""
        if plan.is_jump:
            return [_TOTAL_ITEM]
        surface = plan.ck_surface
        band = synth.CK_DISTANCE_BANDS[max((plan.distance_m - _BAND_START_M) // _BAND_STEP_M, 0)]
        return [
            _TOTAL_ITEM, f"{surface}{band}・着回数",
            f"{surface}{_GOING_NAMES[going_code]}・着回数", f"{VENUE_NAME}{surface}・着回数",
        ]

    @staticmethod
    def _empty_items() -> dict[str, list[int]]:
        return defaultdict(lambda: [0] * synth.CK_SLOTS)
