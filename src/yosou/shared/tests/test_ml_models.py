"""LightGBM・CatBoost のモデルとエンコーダー（設計書 12・13）と、アンサンブル。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ..dataset import PeriodSplitter, TrainingData, TrainingPeriod
from ..feature import PredictionTiming
from ..ml_model import CatBoostEncoder, CatBoostModel, EnsembleModel, LightGbmEncoder, LightGbmModel
from ..ml_model.catboost_encoder import MISSING
from ..ml_model.lightgbm_encoder import OTHER
from ..setting import HyperparameterSettings

TEXT_COLUMNS = {"騎手": "str", "競馬場": "str"}


def test_lightgbm_encoder_groups_rare_and_unseen_values():
    train = pd.DataFrame({
        "騎手": ["A", "A", "A", "B"], "競馬場": ["東京", "東京", "中山", "中山"], "斤量": [55.0] * 4,
    }).astype(TEXT_COLUMNS)
    new = pd.DataFrame({
        "斤量": [56.0, 57.0, 58.0], "騎手": ["A", "Z", None], "競馬場": ["東京", "阪神", None],
    }).astype(TEXT_COLUMNS)
    encoder = LightGbmEncoder(min_category_count=2).fit(train, ["騎手", "競馬場"])
    encoded = encoder.transform(new)
    # 列は学習と同じ並びになる
    assert list(encoded.columns) == ["騎手", "競馬場", "斤量"]
    # 騎手: 出走の少ない B は一覧に入らない。知らない Z は「その他」、欠損値は欠損値のまま
    assert list(encoded["騎手"].cat.categories) == ["A", OTHER]
    assert encoded["騎手"].tolist()[:2] == ["A", OTHER] and pd.isna(encoded["騎手"].iloc[2])
    # 競馬場: 値の種類が少ない列は「その他」にまとめず、知らない値は欠損値にする
    assert encoded["競馬場"].tolist()[0] == "東京" and encoded["競馬場"].isna().tolist() == [False, True, True]


def test_catboost_encoder_turns_missing_categories_into_text():
    features = pd.DataFrame({"騎手": ["A", None], "斤量": [55.0, np.nan]}).astype({"騎手": "str"})
    encoded = CatBoostEncoder(["騎手", "斤量"], ["騎手"]).transform(features)
    assert encoded["騎手"].tolist() == ["A", MISSING] and np.isnan(encoded["斤量"].iloc[1])


@pytest.fixture(scope="module")
def race_day_split(training_data: TrainingData,
                   season_period: TrainingPeriod) -> tuple[TrainingData, TrainingData]:
    """当日の時点の、学習データと検証データ。"""
    split = PeriodSplitter(season_period).split(training_data)
    timing = PredictionTiming.RACE_DAY
    return split.train.for_timing(timing), split.valid.for_timing(timing)


@pytest.mark.parametrize("model_type", [LightGbmModel, CatBoostModel])
def test_model_learns_saves_and_loads(model_type, race_day_split, fast_settings_path: Path,
                                      default_settings_path: Path, tmp_path: Path):
    train, valid = race_day_split
    settings = HyperparameterSettings.load(fast_settings_path, defaults=default_settings_path)
    model = model_type.from_settings(settings).fit(train, valid)
    probability = model.predict_proba(valid)
    assert probability.shape == (len(valid),) and ((probability > 0) & (probability < 1)).all()
    assert 0 < model.tree_count <= 60
    path = tmp_path / model_type.file_name
    model.save(path)
    loaded = model_type.load(path, settings)
    np.testing.assert_allclose(loaded.predict_proba(valid), probability)
    # 列の並びが違っても、学習と同じ並びに直して予測する
    reversed_columns = valid.features[valid.features.columns[::-1]]
    shuffled = TrainingData(valid.ids, reversed_columns, valid.targets, valid.evaluation,
                            valid.catalog, valid.label_name)
    np.testing.assert_allclose(loaded.predict_proba(shuffled), probability)


@pytest.mark.parametrize("model_type", [LightGbmModel, CatBoostModel])
def test_untrained_model_cannot_predict(model_type, race_day_split, default_settings_path: Path):
    _, valid = race_day_split
    settings = HyperparameterSettings.load(None, defaults=default_settings_path)
    with pytest.raises(RuntimeError):
        model_type.from_settings(settings).predict_proba(valid)


class FixedModel:
    """いつも同じ確率を返す、テスト用のモデル。"""

    file_name = "fixed"

    def __init__(self, name: str, probability: list[float]) -> None:
        self.name = name
        self._probability = np.array(probability)

    def predict_proba(self, data) -> np.ndarray:
        return self._probability


def test_ensemble_averages_member_probabilities():
    ensemble = EnsembleModel([FixedModel("甲", [0.1, 0.4]), FixedModel("乙", [0.3, 0.2])])
    assert set(ensemble.predict_members(None)) == {"甲", "乙"}
    np.testing.assert_allclose(ensemble.predict_proba(None), [0.2, 0.3])


def test_ensemble_needs_members():
    with pytest.raises(ValueError):
        EnsembleModel([])
