"""1着のモデルの出発点を、3連単から見た勝率に替える。"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from yosou.form_aptitude_top3.feature import RACE_DAY_CATALOG
from yosou.shared.dataset import BaselineLogit, TrainingData
from yosou.shared.feature import POOL_SUPPORT_FEATURES, PredictionTiming
from yosou.shared.feature.odds import WIN_RATE

from 既存モデルの改善.analysis.variants import ModelVariant

#: 3連単から見た勝率と単勝から見た勝率の比（log）の列（まとまり N の先頭）。
TRIFECTA_RATIO = POOL_SUPPORT_FEATURES[0].name
#: 確率をロジットにするときの端の丸め（``WinBaseline`` と同じ）。
_EDGE = 1e-4
#: 読む表（当日のモデルの表）と、作り方、比べる相手（今の1着のモデルの当日の予測）。
POOL_TABLE = "h2h_pool_ability"
POOL_VARIANT = ModelVariant(POOL_TABLE, "win-pool-race_day", "1着のモデル（出発点を3連単から見た勝率に。当日）",
                            RACE_DAY_CATALOG.columns_for(PredictionTiming.RACE_DAY), uses_baseline=True, timing=PredictionTiming.RACE_DAY)
POOL_CURRENT = (POOL_TABLE, "win-race_day")


class TrifectaWinBaseline:
    """1着のモデル用の学習データ（``WinTargetData.training``。基準はオッズから見た勝率のロジット）の基準を、
    「3連単から見た勝率」のロジットに替える（研究「回収率100超の施策」の施策 1-B）。

    3連単から見た勝率 = exp(3連単から見た勝率と単勝の比（log）) × オッズから見た勝率（表の列から戻す。当日のモデルの材料 N と同じ計算）。
    3連単のオッズが無い出走（比が欠損値）は、元の基準（オッズから見た勝率）のまま。基準が分かる時点は当日。
    """

    def apply(self, data: TrainingData) -> TrainingData:
        if data.baseline is None:
            raise ValueError("1着のモデル用の学習データ（基準あり）を渡してください（WinTargetData.training）")
        ratio = pd.to_numeric(data.features[TRIFECTA_RATIO], errors="coerce")
        market = pd.to_numeric(data.evaluation[WIN_RATE], errors="coerce")
        pool = np.exp(ratio) * market
        fallback = data.baseline.probabilities()
        probability = pd.Series(np.where(pool.notna(), pool, fallback.to_numpy()), index=data.ids.index).clip(_EDGE, 1.0 - _EDGE)
        logit = np.log(probability / (1.0 - probability))
        return replace(data, baseline=BaselineLogit(logit, PredictionTiming.RACE_DAY))
