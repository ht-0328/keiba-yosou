"""段階の予算で、多く買う日を決める材料（何を線と比べるか）。"""

from __future__ import annotations

import math
from enum import Enum

from yosou.form_aptitude_win5_tickets.formation import FormationChoice


class Win5TierSignal(Enum):
    """設計書「近走と適性からWIN5の買い目を決める」15 の 13 の選び方の表。多く買う日を決めるのに線と比べる値。

    - 一律: 比べない（毎回同じ予算）。
    - 本命の確率の積: 5レースの本命のそろえた1着の確率のかけ算（買い目に依らない。採用した決め方）。
    - 判断用の買い目の当たる確率・判断用の買い目の期待値: 判断用の買い目（50点）の値。
    - 追加の点の期待値: （多く買う日の買い目の見積もりの払戻 − 少なく買う日の買い目の見積もりの払戻）÷ 代金の差。
    """

    FLAT = "一律"
    FAVORITE_PRODUCT = "本命の確率の積"
    HIT_PROBABILITY = "判断用の買い目の当たる確率"
    EXPECTED_VALUE = "判断用の買い目の期待値"
    MARGINAL_VALUE = "追加の点の期待値"

    @property
    def label(self) -> str:
        return self.value

    def value_of(self, judge: FormationChoice, small: FormationChoice, large: FormationChoice, favorite_product: float) -> float:
        """その日の、線と比べる値。一律は欠損値（比べない）。``judge`` は判断用、``small``・``large`` は少なく・多く買う日の予算の買い目。"""
        if self is Win5TierSignal.FLAT:
            return math.nan
        if self is Win5TierSignal.FAVORITE_PRODUCT:
            return favorite_product
        if self is Win5TierSignal.HIT_PROBABILITY:
            return judge.hit_probability
        if self is Win5TierSignal.EXPECTED_VALUE:
            return judge.expected_value
        added = large.stake - small.stake
        return (large.expected_payout - small.expected_payout) / added if added > 0 else math.nan

    def format(self, threshold: float) -> str:
        """線の見せ方（確率は小数4桁、期待値は小数2桁）。"""
        if self in (Win5TierSignal.FAVORITE_PRODUCT, Win5TierSignal.HIT_PROBABILITY):
            return f"{threshold:.4f}"
        return f"{threshold:.2f}"
