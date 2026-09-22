"""1レースの結果を決める。"""

from __future__ import annotations

import random
from collections.abc import Sequence

from .synthetic_horse import SyntheticHorse

#: 1レースで、1頭が出走取消になる確率と、1頭が競走中止になる確率。
_SCRATCH_RATE, _STOP_RATE = 0.1, 0.03
#: 着順と人気に混ぜる、運（乱数）の大きさ。
_FINISH_LUCK, _POPULARITY_LUCK = 1.0, 0.7
#: 異常区分コード。
_NORMAL, _SCRATCHED, _STOPPED = "0", "1", "4"


class RaceOutcome:
    """1レースの結果（架空）。能力の高い馬ほど上位に来やすく、人気にもなりやすい。"""

    def __init__(self, rng: random.Random, field: Sequence[SyntheticHorse]) -> None:
        self._scratched = rng.choice(field) if rng.random() < _SCRATCH_RATE else None
        self._stopped = rng.choice(field) if rng.random() < _STOP_RATE else None
        runners = [horse for horse in field if horse is not self._scratched]
        finishers = [horse for horse in runners if horse is not self._stopped]
        self._finish = self._ranks(rng, finishers, _FINISH_LUCK)
        self._popularity = self._ranks(rng, runners, _POPULARITY_LUCK)

    def finish_of(self, horse: SyntheticHorse) -> int:
        """確定着順。着順が付かない馬（出走取消・競走中止）は 0。"""
        return self._finish.get(horse.hid, 0)

    def popularity_of(self, horse: SyntheticHorse) -> int:
        """単勝人気。出走取消の馬は 0。"""
        return self._popularity.get(horse.hid, 0)

    def has_run(self, horse: SyntheticHorse) -> bool:
        return horse is not self._scratched

    def abnormal_code(self, horse: SyntheticHorse) -> str:
        if horse is self._scratched:
            return _SCRATCHED
        if horse is self._stopped:
            return _STOPPED
        return _NORMAL

    def _ranks(self, rng: random.Random, horses: Sequence[SyntheticHorse], luck: float) -> dict[str, int]:
        """能力 + 運 の高い順の順位（血統登録番号 → 順位）。"""
        scores = {horse.hid: horse.ability + rng.gauss(0.0, luck) for horse in horses}
        ordered = sorted(scores, key=scores.__getitem__, reverse=True)
        return {hid: rank for rank, hid in enumerate(ordered, start=1)}
