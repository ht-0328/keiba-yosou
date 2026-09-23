"""検証期間で勝率の重みと Stern の補正を決め、ほかの期間の勝率を出す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_ID
from yosou.shared.dataset.column_names import FINISH

from ..race_probability import FinishOrderProbability, RaceFinishes, RaceStrengthModel, SternExponentFitter
from .strength_features import StrengthFeatures

#: 1着の値。
_WINNER = 1


@dataclass(frozen=True)
class RaceProbabilityFit:
    """検証期間で決めた、勝率の出し方（材料の重み・Stern の補正）。"""

    features: StrengthFeatures
    model: RaceStrengthModel
    lam: float
    mu: float

    def win_probability(self, table: pd.DataFrame) -> np.ndarray:
        """``table`` の行ごとの勝率（レース内で合計 1）。"""
        return self.model.predict(self.features.matrix(table), table[RACE_ID])

    def order_probability(self) -> FinishOrderProbability:
        """着順の並びの確率を出す部品（この補正の強さで）。"""
        return FinishOrderProbability(self.lam, self.mu)

    def summary(self) -> dict[str, float]:
        """表に出す値（材料ごとの重みと λ・μ）。"""
        weights = dict(zip(self.features.names, (float(value) for value in self.model.weights)))
        return {**weights, "λ（2着の寄せ方）": self.lam, "μ（3着の寄せ方）": self.mu}


class RaceProbabilityBuilder:
    """検証期間の行で、材料の重み（条件付きロジット）と Stern の補正（λ・μ）を決める。

    ``RaceStrengthModel`` は勝った馬から重みを決め、``SternExponentFitter`` はその勝率で、実際の2着・3着の並びが
    いちばん起きやすくなる λ・μ を決める。テスト期間の結果はどちらにも使わない。
    """

    def __init__(self, features: StrengthFeatures) -> None:
        self._features = features

    def fit(self, valid: pd.DataFrame) -> RaceProbabilityFit:
        # 着順の無い馬（取消・除外など。欠損値）は 1着ではない。欠損のまま比べると NaN が残り、重みが学べない
        won = valid[FINISH].eq(_WINNER).fillna(False).to_numpy(dtype="float64")
        model = RaceStrengthModel().fit(self._features.matrix(valid), valid[RACE_ID], won)
        probability = model.predict(self._features.matrix(valid), valid[RACE_ID])
        races = RaceFinishes().build(valid[RACE_ID], pd.Series(probability, index=valid.index), valid[FINISH])
        lam, mu = SternExponentFitter().fit(races)
        return RaceProbabilityFit(self._features, model, lam, mu)
