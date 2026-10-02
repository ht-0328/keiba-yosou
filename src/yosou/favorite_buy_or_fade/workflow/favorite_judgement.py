"""学習した一式で、1番人気の近さの点数と判定を出す。"""

from __future__ import annotations

import pandas as pd

from ..decision import BuyDecision
from ..similarity import SimilarityModelSet


class FavoriteJudgement:
    """1番人気の行ごとに、単位・3つの近さの点数・判定を出す（評価と予測で同じものを使う）。

    判定の線（``fade_margin``・``win_margin``）は、一式を学習したときの方針のものを使う。
    """

    def __init__(self, models: SimilarityModelSet) -> None:
        self._models = models
        settings = models.settings
        self._decision = BuyDecision(settings.fade_margin, settings.win_margin)

    def judge(self, features: pd.DataFrame) -> pd.DataFrame:
        """``features`` は、どの時点の特徴量を含んでいてもよい（学習した時点の列だけを使う）。"""
        scores = self._models.scores(features)
        return pd.concat([scores, self._decision.decide(scores)], axis=1)
