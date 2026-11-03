"""オッズだけのモデルを先に学び、それを出発点と比べる相手にする区切りごとの学習。合成データとにせのモデルだけを使う。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, BaselineLogit, TrainingData
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind, PredictionTiming

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, PART_VALID, PREDICTION_COLUMN
from 既存モデルの改善.analysis.windows import TestWindow

from 危険な人気馬を見極める.analysis.odds_only_baseline import ODDS_ONLY_COLUMNS

from 危険な人気馬を見極める.analysis.calibrated_window_trainer import ODDS_ONLY_COLUMN, CalibratedWindowTrainer


class _FakeModel:
    """学習に渡された列と基準を覚え、オッズの列だけなら 0.2、ほかの列も持つなら「基準の確率 + 0.1」を返すにせのモデル。"""

    name = "にせ"
    tree_count = 1
    fitted: list[tuple[tuple[str, ...], np.ndarray]] = []

    @classmethod
    def from_settings(cls, settings):
        return cls()

    def fit(self, train: TrainingData, valid: TrainingData):
        _FakeModel.fitted.append((tuple(train.features.columns), train.baseline.probabilities().to_numpy()))
        self._odds_only = tuple(train.features.columns) == ODDS_ONLY_COLUMNS
        return self

    def predict_proba(self, data: TrainingData) -> np.ndarray:
        if self._odds_only:
            return np.full(len(data), 0.2)
        return data.baseline.probabilities().to_numpy() + 0.1


def _data() -> TrainingData:
    days = [pd.Timestamp(year, 6, 1) for year in (2018, 2019, 2020) for _ in range(4)]
    ids = pd.DataFrame({RACE_ID: [f"r{i}" for i in range(12)], RACE_DATE: days, HORSE_ID: [f"h{i}" for i in range(12)],
                        HORSE_NO: 1})
    columns = (*ODDS_ONLY_COLUMNS, "form")
    features = pd.DataFrame({column: np.arange(12, dtype=float) for column in columns})
    catalog = FeatureCatalog(tuple(Feature(column, "K", FeatureKind.NUMERIC) for column in columns))
    # オッズから計算した基準は 4着以下の確率 0.5（ロジット 0）
    baseline = BaselineLogit(pd.Series(0.0, index=ids.index), PredictionTiming.DAY_BEFORE)
    return TrainingData(ids, features, pd.DataFrame({"y": [0, 1] * 6}), pd.DataFrame({"band": "1番人気"}, index=ids.index),
                        catalog, "y", baseline=baseline)


def test_main_model_starts_from_the_odds_only_model_and_keeps_its_probability():
    _FakeModel.fitted = []
    window = TestWindow("2020年", date(2019, 1, 1), date(2020, 1, 1), date(2020, 12, 31))
    variant = ModelVariant("t", "c", "本番の列", (*ODDS_ONLY_COLUMNS, "form"), uses_baseline=True)
    frame, logs = CalibratedWindowTrainer(None, member_types=(_FakeModel,)).run(_data(), window, variant)
    odds_fit, main_fit = _FakeModel.fitted
    # 1段目はオッズの列だけで、オッズから計算した基準（0.5）から学ぶ
    assert odds_fit[0] == ODDS_ONLY_COLUMNS
    assert odds_fit[1] == pytest.approx([0.5] * 4)
    # 2段目は本番の列で、オッズだけのモデルの確率（0.2）から学ぶ
    assert main_fit[0] == (*ODDS_ONLY_COLUMNS, "form")
    assert main_fit[1] == pytest.approx([0.2] * 4)
    # 予測は検証とテストの全部の行で、比べる相手（オッズだけの確率）も残る
    assert frame[PART].value_counts().to_dict() == {PART_VALID: 4, PART_TEST: 4}
    assert frame[ODDS_ONLY_COLUMN].to_numpy() == pytest.approx([0.2] * 8)
    assert frame[PREDICTION_COLUMN].to_numpy() == pytest.approx([0.3] * 8)
    assert logs[0]["学習の行数"] == 4
