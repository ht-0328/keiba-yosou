"""オッズだけのモデルで基準を置き換える部品（``OddsOnlyBaseline``）。合成データとにせのモデルだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_ID, RACE_DATE, RACE_ID, BaselineLogit, TrainingData
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind, PredictionTiming

from 危険な人気馬を見極める.analysis.odds_only_baseline import ODDS_ONLY_COLUMNS, OddsOnlyBaseline


class _FakeModel:
    """学習に渡された列を覚え、どの行にも決まった確率を返すにせのモデル。"""

    name = "にせ"
    seen: list[tuple[str, ...]] = []

    def __init__(self, probability: float = 0.2) -> None:
        self._probability = probability

    @classmethod
    def from_settings(cls, settings):
        return cls()

    def fit(self, train: TrainingData, valid: TrainingData):
        _FakeModel.seen.append(tuple(train.features.columns))
        return self

    def predict_proba(self, data: TrainingData) -> np.ndarray:
        return np.full(len(data), self._probability)


def _data(baseline: bool = True) -> TrainingData:
    ids = pd.DataFrame({RACE_ID: ["r1", "r2"], RACE_DATE: pd.Timestamp("2024-01-06"), HORSE_ID: ["h1", "h2"]})
    columns = (*ODDS_ONLY_COLUMNS, "近走")
    features = pd.DataFrame({column: [1.0, 2.0] for column in columns})
    catalog = FeatureCatalog(tuple(Feature(column, "K", FeatureKind.NUMERIC) for column in columns))
    logit = BaselineLogit(pd.Series(0.0, index=ids.index), PredictionTiming.DAY_BEFORE) if baseline else None
    return TrainingData(ids, features, pd.DataFrame({"y": [0, 1]}), pd.DataFrame(index=ids.index), catalog, "y",
                        baseline=logit)


def test_fit_uses_only_the_odds_columns():
    _FakeModel.seen = []
    OddsOnlyBaseline.fit(None, _data(), _data(), member_types=(_FakeModel,))
    assert _FakeModel.seen == [ODDS_ONLY_COLUMNS]


def test_attach_replaces_the_baseline_with_the_average_of_the_members():
    baseline = OddsOnlyBaseline([_FakeModel(0.2), _FakeModel(0.4)])
    attached = baseline.attach(_data())
    # 2つのモデルの平均 0.3 が新しい基準。特徴量はそのまま
    assert attached.baseline.probabilities().to_numpy() == pytest.approx([0.3, 0.3])
    assert attached.baseline.known_from == PredictionTiming.DAY_BEFORE
    assert list(attached.features.columns) == [*ODDS_ONLY_COLUMNS, "近走"]


def test_attach_needs_the_baseline_and_members():
    with pytest.raises(ValueError, match="前日・当日"):
        OddsOnlyBaseline([_FakeModel()]).attach(_data(baseline=False))
    with pytest.raises(ValueError, match="モデル"):
        OddsOnlyBaseline([])
