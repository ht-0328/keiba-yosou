"""過去の WIN5 の表から、回ごとの結果（``Win5Outcome``）を作る。"""

from __future__ import annotations

import pandas as pd

from ..repository import LEG_COUNT
from ..repository.win5_columns import CARRY, COMBO, HORSE_NO, LEG, NO_HIT, PAYOUT, RACE_DATE, VOTES
from .win5_outcome import Win5Outcome

#: 組番の1頭ぶんの桁数。
_HORSE_DIGITS = 2


class Win5Outcomes:
    """``Win5HistoryRepository`` の表（1行 = 1回の当たり組）と ``Win5ScratchRepository`` の表（1行 = 取消・除外の1頭）を、
    開催日ごとの ``Win5Outcome`` にまとめる。精算（``Win5Settlement``）に渡す形。"""

    def of(self, history: pd.DataFrame, scratches: pd.DataFrame) -> dict[str, Win5Outcome]:
        """開催日（``YYYY-MM-DD``）→ その回の結果。"""
        scratched = self._scratched(scratches)
        return {day: self._outcome(day, rows, scratched.get(day, {})) for day, rows in history.groupby(RACE_DATE, sort=True)}

    def _outcome(self, day: str, rows: pd.DataFrame, scratched: dict[int, frozenset[int]]) -> Win5Outcome:
        first = rows.iloc[0]
        winners = tuple((self._combo(combo), int(payout)) for combo, payout in zip(rows[COMBO], rows[PAYOUT], strict=True))
        legs = tuple(scratched.get(leg, frozenset()) for leg in range(1, LEG_COUNT + 1))
        return Win5Outcome(day, winners, bool(first[NO_HIT]), legs, int(first[VOTES]), int(first[CARRY]))

    def _combo(self, text: str) -> tuple[int, ...]:
        """組番（``0312051406``）→ 5頭の馬番の並び。"""
        return tuple(int(text[at:at + _HORSE_DIGITS]) for at in range(0, len(text), _HORSE_DIGITS))

    def _scratched(self, scratches: pd.DataFrame) -> dict[str, dict[int, frozenset[int]]]:
        """開催日 → 何レース目 → 取消・除外の馬番。"""
        grouped = scratches.groupby([RACE_DATE, LEG])[HORSE_NO].agg(lambda numbers: frozenset(int(number) for number in numbers))
        result: dict[str, dict[int, frozenset[int]]] = {}
        for (day, leg), numbers in grouped.items():
            result.setdefault(day, {})[int(leg)] = numbers
        return result
