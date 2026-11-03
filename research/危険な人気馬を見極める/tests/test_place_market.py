"""複勝オッズを出発点にした穴馬の予想の学習と、6番人気以下の複勝の成績の表。合成データとにせのモデルだけを使う。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, BaselineLogit, TrainingData
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind, PredictionTiming

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.windows import TestWindow

from 危険な人気馬を見極める.analysis.place_bet_report import PlaceBetReport
from 危険な人気馬を見極める.analysis.place_market_window_trainer import (
    PLACE_MARKET_COLUMN,
    PLACE_MARKET_RATE,
    PlaceMarketWindowTrainer,
)


class _FakeModel:
    """学習に渡された基準を覚え、予測は「基準の確率 + 0.1」を返すにせのモデル。"""

    name = "にせ"
    tree_count = 1
    baselines: list[np.ndarray] = []

    @classmethod
    def from_settings(cls, settings):
        return cls()

    def fit(self, train: TrainingData, valid: TrainingData):
        _FakeModel.baselines.append(train.baseline.probabilities().to_numpy())
        return self

    def predict_proba(self, data: TrainingData) -> np.ndarray:
        return data.baseline.probabilities().to_numpy() + 0.1


def _data() -> TrainingData:
    """2018〜2020年に4頭ずつ。複勝オッズから見た3着以内率は 0.2（2頭目だけ複勝オッズが無い）。"""
    days = [pd.Timestamp(year, 6, 1) for year in (2018, 2019, 2020) for _ in range(4)]
    ids = pd.DataFrame({RACE_ID: [f"r{i}" for i in range(12)], RACE_DATE: days, HORSE_ID: [f"h{i}" for i in range(12)],
                        HORSE_NO: 1})
    rate = [0.2, np.nan, 0.2, 0.2] * 3
    features = pd.DataFrame({PLACE_MARKET_RATE: rate, "form": np.arange(12, dtype=float)})
    catalog = FeatureCatalog(tuple(Feature(column, "M", FeatureKind.NUMERIC) for column in features.columns))
    # 元の基準（単勝オッズから計算した3着以内率）は 0.5（ロジット 0）
    baseline = BaselineLogit(pd.Series(0.0, index=ids.index), PredictionTiming.DAY_BEFORE)
    return TrainingData(ids, features, pd.DataFrame({"y": [0, 1] * 6}), pd.DataFrame(index=ids.index),
                        catalog, "y", baseline=baseline)


def test_starts_from_the_place_market_rate_and_keeps_it_in_the_predictions():
    _FakeModel.baselines = []
    window = TestWindow("2020年", date(2019, 1, 1), date(2020, 1, 1), date(2020, 12, 31))
    variant = ModelVariant("t", "c", "M も使う", (PLACE_MARKET_RATE, "form"), uses_baseline=True)
    frame, _ = PlaceMarketWindowTrainer(None, member_types=(_FakeModel,)).run(_data(), window, variant)
    # 複勝オッズのある馬は 0.2 から、無い馬は元の 0.5 から学ぶ
    assert _FakeModel.baselines[0] == pytest.approx([0.2, 0.5, 0.2, 0.2])
    assert frame["確率"].to_numpy()[:4] == pytest.approx([0.3, 0.6, 0.3, 0.3])
    assert frame[PLACE_MARKET_COLUMN].to_numpy()[:4] == pytest.approx([0.2, np.nan, 0.2, 0.2], nan_ok=True)


def test_refuses_a_variant_without_the_place_market_rate():
    variant = ModelVariant("t", "c", "M なし", ("form",), uses_baseline=True)
    window = TestWindow("2020年", date(2019, 1, 1), date(2020, 1, 1), date(2020, 12, 31))
    with pytest.raises(ValueError, match=PLACE_MARKET_RATE):
        PlaceMarketWindowTrainer(None, member_types=(_FakeModel,)).run(_data(), window, variant)


def _report_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """検証とテストに 7番人気の馬が10頭ずつ（ほかに 2番人気が1頭）。予想が複勝オッズより 0.1 高い2頭だけが3着以内で複勝 400円。"""
    rows, predictions = [], []
    for part, year in (("検証", 2022), ("テスト", 2023)):
        for i in range(10):
            key = f"{part}{i}"
            rows.append({"レースID": key, "馬ID": key, "開催日": pd.Timestamp(year, 1, 1), "確定着順": 2 if i < 2 else 9,
                         "確定の単勝人気": 7, "複勝の払戻": 400.0 if i < 2 else 0.0, PLACE_MARKET_COLUMN: 0.2})
            predictions.append({"レースID": key, "馬ID": key, "開催日": pd.Timestamp(year, 1, 1), "確率": 0.3 if i < 2 else 0.2,
                                "区切り": "2023年", "期間": part})
        rows.append({"レースID": f"{part}f", "馬ID": f"{part}f", "開催日": pd.Timestamp(year, 1, 1), "確定着順": 1,
                     "確定の単勝人気": 2, "複勝の払戻": 110.0, PLACE_MARKET_COLUMN: 0.6})
        predictions.append({"レースID": f"{part}f", "馬ID": f"{part}f", "開催日": pd.Timestamp(year, 1, 1), "確率": 0.9,
                            "区切り": "2023年", "期間": part})
    return pd.DataFrame(rows), pd.DataFrame(predictions)


def test_place_bets_only_on_longshots_above_the_line():
    evaluation, predictions = _report_inputs()
    by_line, chosen = PlaceBetReport().tables(evaluation, {"新": predictions}, lines=(0.0, 0.05))
    # 線 0.00 は 6番人気以下の10頭全部（複勝 80%）、線 +0.05 は2頭だけ（400%）。2番人気の馬は入らない
    assert by_line.rows[0][2:8] == ["10", "20.0%", "80.0%", "10", "20.0%", "80.0%"]
    assert by_line.rows[1][2:9] == ["2", "100.0%", "400.0%", "2", "100.0%", "400.0%", "2023年 400%"]
    # 線を選ぶには検証で 300頭以上買う必要があるので、この小さな例では選べない
    assert chosen.rows[0][1:] == ["", "0", "—", "—"]
