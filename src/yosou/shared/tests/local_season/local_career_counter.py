"""馬ごとの出走別着度数地方の着回数を数える。"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from 合成DB import synth

from ..synthetic_season.race_outcome import RaceOutcome
from ..synthetic_season.synthetic_horse import SyntheticHorse
from .local_race_plan import LocalRacePlan
from .local_season_plan import VENUE_NAME

#: 通算の欄（総合は中央と地方の両方、地方合計は地方だけ。このシーズンの馬は地方しか走らないので同じ数になる）。
_TOTAL_ITEMS = ("総合着回数", "地方合計着回数")
#: 馬場状態コード → 欄の名前での書き方。
_GOING_NAMES = {"1": "良", "2": "稍", "3": "重", "4": "不"}
#: 着回数の6つの列のうち、着外（6着以下と、着順なし）を入れる位置。
_OUT_OF_PLACE_SLOT = synth.CK_SLOTS - 1
#: このシーズンは全部ダート。
_SURFACE = "ダ"


class LocalCareerCounter:
    """馬ごとに、出走別着度数地方の欄ごとの着回数（1着〜5着と着外）を、シーズンの初めから数える。"""

    def __init__(self) -> None:
        self._counts: dict[str, dict[str, list[int]]] = defaultdict(self._empty_items)

    def counts_of(self, horse: SyntheticHorse) -> dict[str, list[int]]:
        """その馬の、いまの時点の着回数（欄の名前 → 6つの回数）。"""
        return self._counts[horse.hid]

    def record_race(self, plan: LocalRacePlan, going_code: str, field: Sequence[SyntheticHorse],
                    outcome: RaceOutcome) -> None:
        """1レースの結果を、出走した馬の着回数に足す。"""
        items = self._items(plan, going_code)
        for horse in field:
            if outcome.has_run(horse):
                slot = self._slot(outcome.finish_of(horse))
                for item in items:
                    self._counts[horse.hid][item][slot] += 1

    def _slot(self, finish: int) -> int:
        """着順を入れる位置。1〜5着はその着順の位置、6着以下と着順なし（競走中止）は着外の位置。"""
        is_in_top5 = 1 <= finish <= _OUT_OF_PLACE_SLOT
        return finish - 1 if is_in_top5 else _OUT_OF_PLACE_SLOT

    def _items(self, plan: LocalRacePlan, going_code: str) -> list[str]:
        """そのレースの結果を足す欄（総合・地方合計・ダートの距離帯・ダートの馬場状態・大井ダ）。"""
        band = next(name for longest, name in synth.ND_DISTANCE_BANDS if longest is None or plan.distance_m <= longest)
        return [
            *_TOTAL_ITEMS, f"{_SURFACE}{band}・着回数", f"{_SURFACE}{_GOING_NAMES[going_code]}・着回数",
            f"{VENUE_NAME}{_SURFACE}・着回数",
        ]

    @staticmethod
    def _empty_items() -> dict[str, list[int]]:
        return defaultdict(lambda: [0] * synth.CK_SLOTS)
