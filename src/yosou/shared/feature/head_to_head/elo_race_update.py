"""1レースの着順から、出走馬のレーティングの上げ下げを出す。"""

from __future__ import annotations

import numpy as np

from .head_to_head_columns import SCALE


class EloRaceUpdate:
    """Elo の式を、1レースの全部の2頭の組に当てて、1頭ごとの上げ下げにまとめる。

    2頭の組ごとに、勝つ見込み E = 1 ÷ (1 + 10^((相手 − 自分) ÷ 400)) と、結果 S（先着 1・同着 0.5・後着 0）の差を取り、
    相手の数で平均して、その馬の K を掛ける。例: 3頭が同じレーティングで、1着なら (1 − 0.5) × 2 ÷ 2 × K = K ÷ 2 上がり、
    2着なら 0、3着なら K ÷ 2 下がる。相手の数で平均するので、頭数が違っても1回の上げ下げは −K〜+K に収まる。
    """

    def deltas(self, ratings: np.ndarray, finishes: np.ndarray, k_factors: np.ndarray) -> np.ndarray:
        """出走馬ごとの上げ下げ（``ratings`` と同じ並び）。``finishes`` は着順、``k_factors`` は馬ごとの K。1頭だけなら 0。"""
        count = len(ratings)
        if count < 2:
            return np.zeros(count)
        # 行 = 自分、列 = 相手。自分と自分の組は、見込みも結果も 0.5 なので差が 0 になり、足しても影響しない
        expected = 1.0 / (1.0 + 10.0 ** ((ratings[None, :] - ratings[:, None]) / SCALE))
        beaten = (finishes[:, None] < finishes[None, :]).astype(float)
        tied = (finishes[:, None] == finishes[None, :]).astype(float)
        actual = beaten + 0.5 * tied
        return k_factors * (actual - expected).sum(axis=1) / (count - 1)
