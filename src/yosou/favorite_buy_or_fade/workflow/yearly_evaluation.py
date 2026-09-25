"""1年ごとに学習し直して、その年の1番人気を判定する。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.dataset import HORSE_NAME, HORSE_NO, RACE_DATE, RACE_ID, TrainingData
from yosou.shared.dataset.column_names import PLACE_PAYOUT, WIN_PAYOUT

from ..dataset import GROUPS
from ..setting import BuyOrFadeSettings
from .favorite_judgement import FavoriteJudgement
from .similarity_training import SimilarityTraining

#: 評価の年の列。
YEAR = "年"
#: 判定の結果の表に残す列（ID と、払戻）。
_ID_COLUMNS = [RACE_ID, RACE_DATE, HORSE_NO, HORSE_NAME]
_PAYOUT_COLUMNS = [WIN_PAYOUT, PLACE_PAYOUT]


class YearlyEvaluation:
    """1年ごとの評価（設計書 16）。評価する年ごとに、方針の「学習の最初の年」からその前年までで学習し直し、
    その年の1番人気を判定する。評価する年のデータは、その年の学習に入らない。
    """

    def __init__(self, settings: BuyOrFadeSettings) -> None:
        self._settings = settings

    def run(self, data: TrainingData) -> pd.DataFrame:
        """1行 = 評価した年の1番人気1頭。列は 年・ID・単位・3つの近さ・判定・3つのグループ・単勝と複勝の払戻。"""
        years = range(self._settings.first_year, self._settings.last_year + 1)
        parts = [self._judged_year(data, year) for year in years]
        return pd.concat([part for part in parts if not part.empty], ignore_index=True)

    def _judged_year(self, data: TrainingData, year: int) -> pd.DataFrame:
        test = data.between(date(year, 1, 1), date(year + 1, 1, 1))
        if len(test) == 0:
            return pd.DataFrame()
        train = data.between(date(self._settings.train_first_year, 1, 1), date(year, 1, 1))
        judged = FavoriteJudgement(SimilarityTraining(self._settings).train(train)).judge(test.features)
        return pd.concat([
            pd.Series(year, index=test.ids.index, name=YEAR), test.ids[_ID_COLUMNS], judged,
            test.targets[list(GROUPS)], test.evaluation[_PAYOUT_COLUMNS],
        ], axis=1)
