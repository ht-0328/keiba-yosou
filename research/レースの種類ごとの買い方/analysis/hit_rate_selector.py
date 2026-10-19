"""選ぶ期間だけで、的中率を上げることを条件にして「決まり × 絞り方」を1つ選ぶ（docs/04 の 4）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .buy_rule import BuyRule
from .filter_selector import FilterSelector
from .profit_bootstrap import ProfitBootstrap
from .rule_day_table import HIT_RACES, PAYOUT, POINTS, RACES

#: 選ぶ条件（docs/04 の 4）。当たったレースの数・回収率・回収率の幅の下の端・比べる相手に対する的中率の倍率。
MIN_HITS, MIN_PAYBACK, MIN_LOWER, HIT_RATE_RATIO = 50, 1.10, 1.00, 1.1


@dataclass(frozen=True)
class HitRatePick:
    """選んだ決まりと絞り方と、選ぶ期間での回収率・幅の下の端・的中率（割合）。選べなければ ``rule`` が None。"""

    rule: BuyRule | None
    filter_text: str
    payback: float
    lower: float
    hit_rate: float
    eligible: int


class HitRateSelector:
    """``FilterSelector`` の候補（絞り方 × 決まり）のうち、選ぶ期間（``years`` の年）の成績が条件
    （当たったレース ``MIN_HITS`` 以上・回収率 ``MIN_PAYBACK`` 以上・回収率の 90% の幅の下の端 ``MIN_LOWER`` 以上・
    的中率が比べる相手の ``HIT_RATE_RATIO`` 倍以上）を全部満たすもののうち、幅の下の端がいちばん高い1つを選ぶ。"""

    def __init__(self, selector: FilterSelector, days: Sequence[pd.Timestamp], rules: Sequence[BuyRule]) -> None:
        self._selector = selector
        self._years = pd.DatetimeIndex(days).year.to_numpy()
        self._rules = list(rules)

    def pick(self, years: Sequence[int], base_hit_rate: float, yearly_floor: bool = False,
             max_cap: float | None = None) -> tuple[HitRatePick, np.ndarray | None]:
        """（選んだもの, その組み合わせの開催日ごとの成績 [開催日, 4]。選べなければ None）。

        ``yearly_floor`` なら、選ぶ期間の各年で回収率 100% 以上の組み合わせだけ。``max_cap`` があれば、オッズの上限がそれ以下の決まりだけ
        （docs/04 の 7 の2回目）。"""
        stack = self._selector.stack
        inside = np.flatnonzero(np.isin(self._years, list(years)))
        flat = stack.reshape(-1, *stack.shape[2:])[:, inside, :].astype(float)
        points, payout = flat[:, :, POINTS].sum(axis=1), flat[:, :, PAYOUT].sum(axis=1)
        races, hits = flat[:, :, RACES].sum(axis=1), flat[:, :, HIT_RACES].sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            payback = payout / (100.0 * points)
            hit_rate = hits / races
        eligible = (hits >= MIN_HITS) & (payback >= MIN_PAYBACK) & (hit_rate >= HIT_RATE_RATIO * base_hit_rate)
        if yearly_floor:
            for year in years:
                cells = flat[:, self._years[inside] == year, :]
                eligible &= cells[:, :, PAYOUT].sum(axis=1) >= 100.0 * cells[:, :, POINTS].sum(axis=1)
        if max_cap is not None:
            allowed = np.array([rule.cap <= max_cap for rule in self._rules])
            eligible &= np.tile(allowed, len(self._selector.filter_texts))
        if not eligible.any():
            return HitRatePick(None, "選べない", float("nan"), float("nan"), float("nan"), 0), None
        chosen = np.flatnonzero(eligible)
        lower = ProfitBootstrap(len(inside)).lower_rate((100.0 * flat[chosen, :, POINTS]).T, flat[chosen, :, PAYOUT].T)
        passed = lower >= MIN_LOWER
        if not passed.any():
            return HitRatePick(None, "選べない（幅の下の端が届かない）", float("nan"), float("nan"), float("nan"), int(eligible.sum())), None
        best = chosen[np.flatnonzero(passed)[int(np.argmax(lower[passed]))]]
        candidate, rule = divmod(int(best), len(self._rules))
        pick = HitRatePick(self._rules[rule], self._selector.filter_texts[candidate], float(payback[best]),
                           float(lower[np.flatnonzero(chosen == best)[0]]), float(hit_rate[best]), int(passed.sum()))
        return pick, stack[candidate, rule].astype(float)
