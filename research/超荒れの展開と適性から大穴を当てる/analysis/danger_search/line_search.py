"""人気帯ごとの固定の線を、探索の期間の成績だけで1つずつ動かして選ぶ。"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .danger_evaluator import Evaluation
from .ticket_metrics import DANGER_RULES, EXPLORE, TOTAL

#: 人気帯（線を動かす順。1番人気の線がいちばん効くので先）。
BANDS: tuple[str, ...] = ("1番人気", "2〜3番人気", "4〜5番人気")
#: 線の候補（危険度 = 4着以下の確率 − 市場から見た4着以下の確率。None はその人気帯を消にしない）。
GRID: dict[str, tuple[float | None, ...]] = {
    "1番人気": (0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.25, None),
    "2〜3番人気": (0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20, None),
    "4〜5番人気": (0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15, None),
}
#: 選ぶのに見る成績（探索の期間だけ）: 消を使う買い方と全部の合計の、的中率と回収率。
JUDGED: tuple[tuple[str, str], ...] = ((DANGER_RULES, "hit_rate"), (DANGER_RULES, "return_rate"), (TOTAL, "hit_rate"), (TOTAL, "return_rate"))


@dataclass(frozen=True)
class Trial:
    """線の組1つの結果。``margins`` は ``JUDGED`` の順に、基準（今の消）との差（ポイント）。``score`` は（差の最小, 差の合計）。"""

    lines: dict[str, float | None]
    evaluation: Evaluation
    margins: tuple[float, ...]

    @property
    def score(self) -> tuple[float, float]:
        return (min(self.margins), sum(self.margins))

    @property
    def satisfied(self) -> bool:
        """探索の期間で、見る成績の全部が基準以上か。"""
        return all(margin >= 0 for margin in self.margins)

    def label(self) -> str:
        return "・".join(f"{band} {'—' if line is None else f'{line * 100:.0f}'}" for band, line in self.lines.items())


class LineSearch:
    """``evaluate``（線の組 → ``Evaluation``）を、1つの人気帯の線だけを候補の中で動かして全部試し、点のいちばん高い線に移す。
    これを人気帯の順に、``passes`` 回まわす（動かなくなったら止める）。点は探索の期間の ``JUDGED`` の成績の、基準との差の最小
    （同じなら合計）。確認の期間の成績は選ぶのに使わない。同じ線の組は二度評価しない。"""

    def __init__(self, evaluate: Callable[[dict[str, float | None]], Evaluation], baseline: Evaluation,
                 grid: dict[str, tuple[float | None, ...]] = GRID, passes: int = 2) -> None:
        self._evaluate = evaluate
        self._baseline = baseline
        self._grid = grid
        self._passes = passes
        self.trials: dict[tuple, Trial] = {}

    def run(self, start: dict[str, float | None]) -> Trial:
        current = {band: self._snap(band, start.get(band)) for band in BANDS}
        best = self._trial(current)
        for _ in range(self._passes):
            moved = False
            for band in BANDS:
                for line in self._grid[band]:
                    trial = self._trial({**current, band: line})
                    if trial.score > best.score:
                        best, moved = trial, True
                current = dict(best.lines)
            if not moved:
                break
        return best

    def _trial(self, lines: dict[str, float | None]) -> Trial:
        key = tuple(lines[band] for band in BANDS)
        if key not in self.trials:
            started = time.monotonic()
            evaluation = self._evaluate(lines)
            margins = tuple((evaluation.value(group, EXPLORE, column) - self._baseline.value(group, EXPLORE, column)) * 100
                            for group, column in JUDGED)
            self.trials[key] = Trial(dict(lines), evaluation, margins)
            print(f"  線 {self.trials[key].label()}: 差 {' / '.join(f'{m:+.2f}' for m in margins)}"
                  f"（{evaluation.computed_races:,} レースを数え直し。{time.monotonic() - started:.0f}秒）", file=sys.stderr, flush=True)
        return self.trials[key]

    def _snap(self, band: str, value: float | None) -> float | None:
        """出発点の線を、候補の中でいちばん近い値にそろえる。"""
        if value is None or np.isnan(value):
            return None
        candidates = [line for line in self._grid[band] if line is not None]
        return min(candidates, key=lambda line: abs(line - value))
