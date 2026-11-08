"""並べ替えの点数を、人気薄の1着の確率に直す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RankProbability:
    """1頭の確率 = そのレースの人気薄の市場合計 × ``scale`` × レースの人気薄の中での softmax（点数 = 出発点のロジット ＋ 上げ下げ）。
    ``scale`` は学習の期間の「人気薄が実際に勝った数 ÷ 市場が見た数」（市場は人気薄の勝ちを多めに見るので、その分を直す）。"""

    scale: float

    @staticmethod
    def scale_of(label: pd.Series, market: pd.Series) -> float:
        total = float(market.sum())
        return float(label.sum()) / total if total > 0 else 1.0

    def of(self, race_ids: pd.Series, score: np.ndarray, market: pd.Series) -> np.ndarray:
        frame = pd.DataFrame({"race": race_ids.to_numpy(), "score": score, "market": market.to_numpy()})
        shifted = frame["score"] - frame.groupby("race")["score"].transform("max")
        weight = np.exp(shifted)
        share = weight / weight.groupby(frame["race"]).transform("sum")
        longshot_total = frame.groupby("race")["market"].transform("sum") * self.scale
        return (share * longshot_total).to_numpy()
