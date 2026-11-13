"""配当の見積もりの式の材料（組ごとの2つの値）を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .win5_rules import PAYOUT_RATE, TICKET_YEN

#: 材料の列の名前（式の傾きの順）。
INVERSE_LOG = "市場の組の確率の逆数の対数"
CARRY_LOG = "キャリーオーバーの比の対数"
FEATURE_COLUMNS: tuple[str, ...] = (INVERSE_LOG, CARRY_LOG)


class PayoutFeatures:
    """組1つにつき、市場の組の確率の逆数の対数と、キャリーオーバーの比の対数を作る（設計書 09 の 2.）。

    キャリーオーバーの比 = log(1 + キャリーオーバー金額初期 ÷（発売票数の見積もり × 100円 × 払戻率））。
    値は1つでも、組の数だけの並びでもよい（予測のときは、その日の全部の組に同じキャリーオーバーと発売票数を使う）。
    """

    def of(self, market_probability: np.ndarray | pd.Series, carry: float | np.ndarray | pd.Series,
           pool_votes: float | np.ndarray | pd.Series) -> pd.DataFrame:
        """列は ``FEATURE_COLUMNS``。市場の組の確率は 0 より大きいこと。"""
        probability = np.asarray(market_probability, dtype=float).ravel()
        sales_share = np.asarray(pool_votes, dtype=float) * TICKET_YEN * PAYOUT_RATE
        carry_ratio = np.asarray(carry, dtype=float) / sales_share
        return pd.DataFrame({
            INVERSE_LOG: -np.log(probability),
            CARRY_LOG: np.broadcast_to(np.log1p(carry_ratio), probability.shape),
        })
