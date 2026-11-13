"""段階の予算の買い方（少なく買う日と多く買う日の予算と、多く買う日の決め方）の1つと、確かめる候補の一覧。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from yosou.form_aptitude_win5_tickets.formation import (
    DEFAULT_MIN_VALUE,
    DEFAULT_ORDERING,
    FAVORITE_PRODUCT_LINE,
    JUDGE_BUDGET,
    LARGE_BUDGET,
    SMALL_BUDGET,
    FormationChoice,
)

from 印の成績.win5_strategy import Win5Strategy
from 印の成績.win5_tier_signal import Win5TierSignal

#: 段階の予算の買う日の判断（判断用の買い目。1着の確率の順・50点・線 1.25。候補は全部これで買う日を決める）。
TIER_JUDGE = Win5Strategy(DEFAULT_ORDERING, JUDGE_BUDGET, DEFAULT_MIN_VALUE)


@dataclass(frozen=True)
class Win5TierStrategy:
    """設計書「近走と適性からWIN5の買い目を決める」15 の 13・16 の「段階の予算の確かめ」。``signal`` が多く買う日の決め方、
    ``threshold`` がその線（``signal`` の値がこの値以上なら多く買う）、``small``・``large`` が少なく買う日・多く買う日の予算（点）。
    一律の候補は ``small == large``。買う日の判断は ``TIER_JUDGE`` で、候補の間で変えない。"""

    signal: Win5TierSignal
    threshold: float
    small: int
    large: int

    @property
    def flat(self) -> bool:
        """毎回同じ予算か。"""
        return self.small == self.large

    @property
    def rule_text(self) -> str:
        """``本命の確率の積 0.0025 以上は 100点、ほか 30点`` の形（一律なら ``一律 30点``）。"""
        if self.flat:
            return f"一律 {self.large}点"
        return f"{self.signal.label} {self.signal.format(self.threshold)} 以上は {self.large}点、ほか {self.small}点"

    @property
    def label(self) -> str:
        """表の「買い方」の列（``段階の予算（本命の確率の積 0.0025 以上は 100点、ほか 30点）``）。"""
        return f"段階の予算（{self.rule_text}）"

    @property
    def budgets(self) -> tuple[int, ...]:
        """買い目を組む予算（判断用も含む。小さい順）。"""
        return tuple(sorted({TIER_JUDGE.budget, self.small, self.large}))

    def is_large(self, judge: FormationChoice, small: FormationChoice, large: FormationChoice, favorite_product: float) -> bool:
        """その日が多く買う日か（一律の候補は毎回 False。値が欠損値なら False）。"""
        if self.flat:
            return False
        value = self.signal.value_of(judge, small, large, favorite_product)
        return not math.isnan(value) and value >= self.threshold

    def budget_for(self, large_day: bool) -> int:
        return self.large if large_day else self.small


#: 採用した決め方（predict の既定と同じ値）。
ADOPTED_TIER = Win5TierStrategy(Win5TierSignal.FAVORITE_PRODUCT, FAVORITE_PRODUCT_LINE, SMALL_BUDGET, LARGE_BUDGET)
#: 確かめた候補（設計書 15 の 13 の選び方の表。固定の一覧）。一律 50点は「この予想」の 1着の確率の順・50点・線 1.25 と同じ買い目。
TIER_CANDIDATES: tuple[Win5TierStrategy, ...] = (
    Win5TierStrategy(Win5TierSignal.FLAT, math.nan, 30, 30),
    Win5TierStrategy(Win5TierSignal.FLAT, math.nan, 50, 50),
    Win5TierStrategy(Win5TierSignal.FLAT, math.nan, 100, 100),
    Win5TierStrategy(Win5TierSignal.FLAT, math.nan, 200, 200),
    ADOPTED_TIER,
    Win5TierStrategy(Win5TierSignal.FAVORITE_PRODUCT, FAVORITE_PRODUCT_LINE, 30, 150),
    Win5TierStrategy(Win5TierSignal.FAVORITE_PRODUCT, FAVORITE_PRODUCT_LINE, 30, 200),
    Win5TierStrategy(Win5TierSignal.HIT_PROBABILITY, 0.0175, 30, 100),
    Win5TierStrategy(Win5TierSignal.EXPECTED_VALUE, 1.50, 30, 100),
    Win5TierStrategy(Win5TierSignal.MARGINAL_VALUE, 1.00, 30, 100),
)
#: 候補の買い目を組むのに要る予算（判断用を含む）。
TIER_BUDGETS: tuple[int, ...] = tuple(sorted({budget for strategy in TIER_CANDIDATES for budget in strategy.budgets}))
