"""年ごとに、その年より前だけで「決まり × 絞り方」を選び、その年の成績を足していく（docs/03 の 4 の B）。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .buy_rule import BuyRule
from .profit_bootstrap import ProfitBootstrap
from .rule_day_table import HIT_RACES, PAYOUT, POINTS
from .walk_forward_selector import FIRST_YEAR

#: 選ぶのに要る、選ぶ期間の当たったレースの数（docs/03 の 4）。
MIN_HITS = 150


@dataclass(frozen=True)
class FilterChoice:
    """ある年に選んだ決まりと絞り方（無ければ ``None``）と、選ぶ期間での回収率の下の端。"""

    year: int
    rule: BuyRule | None
    filter_text: str
    lower_rate: float


@dataclass(frozen=True)
class _Candidate:
    """絞り方の候補1つ。``trait`` の帯 ``low``〜``high``（両端を含む）のレースだけ。"""

    trait: str
    low: int
    high: int
    text: str


class FilterSelector:
    """中身ごとの配列 {中身: [決まり, 帯, 開催日, 4]}（``RuleDayTable`` を帯の列で作ったもの）から、絞り方の候補
    （絞らない・帯 k 以下・帯 k 以上・危険な人気馬が いない／いる）と決まりの全部の組み合わせを並べ、
    年ごとに、選ぶ期間（``FIRST_YEAR``〜前の年）の回収率の 90% の幅の下の端がいちばん高い組み合わせを選ぶ。"""

    def __init__(self, tables: Mapping[str, np.ndarray], days: Sequence[pd.Timestamp], rules: Sequence[BuyRule]) -> None:
        self._years = pd.DatetimeIndex(days).year.to_numpy()
        self._rules = list(rules)
        self._candidates = self._candidates_of(tables)
        self._stack = np.stack([tables[item.trait][:, item.low:item.high + 1].sum(axis=1) for item in self._candidates]).astype(np.float32)

    def run(self, years: Sequence[int]) -> tuple[np.ndarray, list[FilterChoice]]:
        """（開催日ごとの成績 [開催日, 4]。選んだ年以外は 0, 選んだ一覧）。"""
        result = np.zeros(self._stack.shape[2:], dtype=float)
        choices = []
        for year in years:
            choice, cells = self.choose(year)
            choices.append(choice)
            if cells is not None:
                result[self._years == year] += cells[self._years == year]
        return result, choices

    def choose(self, year: int) -> tuple[FilterChoice, np.ndarray | None]:
        """``year`` より前だけで選ぶ。（選んだもの, その組み合わせの開催日ごとの成績 [開催日, 4]。選べなければ None）。"""
        train = np.flatnonzero((self._years >= FIRST_YEAR) & (self._years < year))
        flat = self._stack.reshape(-1, *self._stack.shape[2:])[:, train, :]
        eligible = flat[:, :, HIT_RACES].sum(axis=1) >= MIN_HITS
        if not eligible.any():
            return FilterChoice(year, None, "買わない", float("nan")), None
        lower = ProfitBootstrap(len(train)).lower_rate((100.0 * flat[:, :, POINTS]).T, flat[:, :, PAYOUT].T)
        lower[~eligible] = -np.inf
        at = int(np.argmax(lower))
        candidate, rule = divmod(at, len(self._rules))
        cells = self._stack[candidate, rule].astype(float)
        return FilterChoice(year, self._rules[rule], self._candidates[candidate].text, float(lower[at])), cells

    @staticmethod
    def _candidates_of(tables: Mapping[str, np.ndarray]) -> list[_Candidate]:
        names = list(tables)
        first = names[0]
        items = [_Candidate(first, 0, tables[first].shape[1] - 1, "絞らない")]
        for trait in names:
            count = tables[trait].shape[1]
            if trait == "has_danger":
                items += [_Candidate(trait, 0, 0, "危険な人気馬がいない"), _Candidate(trait, 1, 1, "危険な人気馬がいる")]
                continue
            items += [_Candidate(trait, 0, top, f"{trait} の帯 {top + 1} 以下") for top in range(count - 1)]
            items += [_Candidate(trait, low, count - 1, f"{trait} の帯 {low + 1} 以上") for low in range(1, count)]
        return items
