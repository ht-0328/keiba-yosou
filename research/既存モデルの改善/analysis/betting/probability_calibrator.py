"""当たる確率のずれを、券種 × オッズの帯ごとに直す。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from .candidate_columns import ODDS, PRICE, PROBABILITY, RAW_PROBABILITY, TICKET, VALUE
from .payout_table import PAYOUT

#: オッズの帯（確率のずれの表と同じ）。
ODDS_BANDS = [0, 2, 5, 10, 30, 100, 300, 1000, 10_000, 1e9]
#: 当たりの少ない帯の比を 1 に寄せる強さ（当たり何回ぶんを「予想どおり」として足すか）。
_PRIOR_HITS = 5.0
#: 比の上限（見積もりが低すぎる帯を上げすぎないように）。
_MAX_RATIO = 1.5


class ProbabilityCalibrator:
    """当たる確率を、券種 × オッズの帯ごとに「実際に当たった割合 ÷ 予想した確率の平均」の比で直す。

    比は検証期間の買い目の候補（払戻つき）で決める。当たりの少ない帯は比が偶然で振れるので、当たり ``_PRIOR_HITS`` 回ぶんの
    「予想どおり」を足して 1 に寄せる。例: 3連単の 1000倍以上で、予想の合計 30回・実際 12回なら、比は (12+5)/(30+5) ≒ 0.49 で、
    その帯の確率を半分にする。見積もりすぎの帯の期待値が見かけだけ高くならないようにするため。
    """

    def __init__(self, ratios: Mapping[tuple[str, float], float]) -> None:
        self._ratios = dict(ratios)

    @classmethod
    def learn(cls, candidates: pd.DataFrame) -> ProbabilityCalibrator:
        """検証期間の買い目の候補（``PAYOUT`` の列を持つ）から、券種 × オッズの帯ごとの比を決める。"""
        band = pd.cut(candidates[ODDS], ODDS_BANDS, right=False).map(lambda interval: interval.left).astype(float)
        summary = candidates.assign(当たり=candidates[PAYOUT] > 0, 帯=band).groupby([TICKET, "帯"], observed=True).agg(
            当たり=("当たり", "sum"), 予想=(PROBABILITY, "sum"))
        ratios = ((summary["当たり"] + _PRIOR_HITS) / (summary["予想"] + _PRIOR_HITS)).clip(upper=_MAX_RATIO)
        return cls(ratios.to_dict())

    @property
    def ratios(self) -> dict[tuple[str, float], float]:
        return dict(self._ratios)

    def apply(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """当たる確率と期待値を直した表（直す前の確率は ``RAW_PROBABILITY`` に残す）。知らない帯は比 1。"""
        band = pd.cut(candidates[ODDS], ODDS_BANDS, right=False).map(lambda interval: interval.left).astype(float)
        keys = list(zip(candidates[TICKET], band))
        ratio = np.array([self._ratios.get(key, 1.0) for key in keys], dtype="float64")
        probability = np.clip(candidates[PROBABILITY].to_numpy(dtype="float64") * ratio, 0.0, 1.0)
        return candidates.assign(**{RAW_PROBABILITY: candidates[PROBABILITY], PROBABILITY: probability,
                                    VALUE: probability * candidates[PRICE]})
