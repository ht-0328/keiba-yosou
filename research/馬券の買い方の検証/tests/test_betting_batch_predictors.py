"""契約: 一括予測の部品は、期間の学習データを時点の列にそろえて保存済みモデルに渡し、ID 列・評価用の列・確率の列を持つ表を返す。

モデルと置き場は、定数の確率を返す代役（合成データ）。実DB も学習済みモデルも使わない。
"""

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import (
    HORSE_ID,
    HORSE_NAME,
    HORSE_NO,
    RACE_DATE,
    RACE_ID,
    RACE_NO,
    VENUE,
    TrainingData,
)
from yosou.shared.dataset.column_names import FINISH, PLACE_PAYOUT, POPULARITY, WIN_ODDS, WIN_PAYOUT
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.feature import Feature
from yosou.shared.feature.feature_catalog import FeatureCatalog
from yosou.shared.feature.feature_kind import FeatureKind
from yosou.upset_level.dataset import BetType, UpsetLevel
from yosou.upset_level.workflow import UPSET_OR_MORE

from 馬券の買い方の検証.analysis.prediction import ACTUAL_LEVEL, RaceBatchPredictor, RunnerBatchPredictor

#: 距離は木曜から、馬体重は当日からしか分からない特徴量（時点の列のそろえ方を確かめる）。
_CATALOG = FeatureCatalog((
    Feature("距離", "A", FeatureKind.NUMERIC),
    Feature("馬体重", "B", FeatureKind.NUMERIC, PredictionTiming.RACE_DAY),
))


class _ConstantModel:
    """どの行にも同じ確率を返す代役。渡された特徴量の列を覚えておく。"""

    def __init__(self, name: str, value) -> None:
        self.name = name
        self._value = np.asarray(value, dtype=float)
        self.seen_columns: list[str] = []

    def predict_proba(self, data):
        self.seen_columns = list(data.features.columns)
        if self._value.ndim == 0:
            return np.full(len(data.features), float(self._value))
        return np.tile(self._value, (len(data.features), 1))


class _StubRepository:
    """``ModelRepository`` の代役。時点によらず同じモデルを返す。"""

    def __init__(self, *models) -> None:
        self._models = models

    def load(self, timing):
        return list(self._models)


def _runner_data() -> TrainingData:
    ids = pd.DataFrame({
        RACE_ID: ["2025070605010101"] * 2, RACE_DATE: pd.to_datetime(["2025-07-06"] * 2),
        HORSE_ID: ["2019100001", "2019100002"], HORSE_NO: [1, 2], HORSE_NAME: ["ウマ01", "ウマ02"],
    })
    features = pd.DataFrame({"距離": [1600, 1600], "馬体重": [480, 500]})
    targets = pd.DataFrame({"3着以内": [1, 0]})
    evaluation = pd.DataFrame({
        FINISH: [1, 5], WIN_ODDS: [5.4, 12.0], POPULARITY: [2, 6], WIN_PAYOUT: [540, 0], PLACE_PAYOUT: [180, 0],
    })
    return TrainingData(ids, features, targets, evaluation, _CATALOG, "3着以内")


def _race_data() -> TrainingData:
    ids = pd.DataFrame({
        RACE_ID: ["2025070605010101", "2025070605010102"], RACE_DATE: pd.to_datetime(["2025-07-06"] * 2),
        VENUE: ["東京", "東京"], RACE_NO: [1, 2],
    })
    features = pd.DataFrame({"距離": [1600, 2000], "馬体重": [480, 500]})
    targets = pd.DataFrame({BetType.WIN.column_name: [0, 2], BetType.TRIO.column_name: [1, np.nan]})
    evaluation = pd.DataFrame({"1〜3着の人気の和": [6, 15]})
    return TrainingData(ids, features, targets, evaluation, _CATALOG, BetType.WIN.column_name, UpsetLevel.class_labels())


def test_runner_predictor_averages_models_and_keeps_ids_and_evaluation():
    lightgbm, catboost = _ConstantModel("LightGBM", 0.6), _ConstantModel("CatBoost", 0.4)
    table = RunnerBatchPredictor(_StubRepository(lightgbm, catboost), "3着以内に入る確率").predict(_runner_data())
    assert list(table.columns) == [
        RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO, HORSE_NAME,
        FINISH, WIN_ODDS, POPULARITY, WIN_PAYOUT, PLACE_PAYOUT,
        "3着以内に入る確率", "LightGBM", "CatBoost",
    ]
    assert list(table["3着以内に入る確率"]) == pytest.approx([0.5, 0.5])
    assert list(table[HORSE_NO]) == [1, 2]
    assert lightgbm.seen_columns == ["距離", "馬体重"]


def test_runner_predictor_passes_only_the_columns_known_at_the_timing():
    model = _ConstantModel("LightGBM", 0.3)
    RunnerBatchPredictor(_StubRepository(model), "3着以内に入る確率", PredictionTiming.THURSDAY).predict(_runner_data())
    assert model.seen_columns == ["距離"]


def test_runner_predictor_rejects_empty_data():
    empty = _runner_data().between(pd.Timestamp("2030-01-01").date(), None)
    with pytest.raises(LookupError):
        RunnerBatchPredictor(_StubRepository(_ConstantModel("LightGBM", 0.3)), "p").predict(empty)


def test_race_predictor_makes_one_block_per_bet_with_actual_level():
    repositories = {
        BetType.WIN: _StubRepository(
            _ConstantModel("LightGBM", [0.7, 0.2, 0.1, 0.0]), _ConstantModel("CatBoost", [0.5, 0.2, 0.2, 0.1]),
        ),
        BetType.TRIO: _StubRepository(_ConstantModel("LightGBM", [0.1, 0.2, 0.3, 0.4])),
    }
    table = RaceBatchPredictor(repositories).predict(_race_data())
    assert len(table) == 4
    assert list(table["券種"]) == ["単勝", "単勝", "3連複", "3連複"]
    win = table[table["券種"] == "単勝"]
    assert list(win[UPSET_OR_MORE]) == pytest.approx([0.4, 0.4])
    assert list(win["固い"]) == pytest.approx([0.6, 0.6])
    assert list(win[ACTUAL_LEVEL]) == [0, 2]
    trio = table[table["券種"] == "3連複"]
    assert list(trio["いちばん高いクラス"]) == ["超荒れ", "超荒れ"]
    assert trio[ACTUAL_LEVEL].isna().tolist() == [False, True]
    assert list(table["1〜3着の人気の和"]) == [6, 15, 6, 15]
