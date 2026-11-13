"""人気薄の1着の予想（段2）の部品を、架空の値で確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.combined_win_share import CombinedWinShare
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.evaluation_frame import CURRENT, MARKET, EvaluationFrame
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import LongshotData
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.ordering_capture_table import OrderingCaptureTable
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.race_weights import RaceWeights
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.rank_lightgbm import RankLightGbm
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.rank_probability import RankProbability
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.type_features import COLUMNS, TypeFeatures
from WIN5で人気薄の勝ち馬を狙う.analysis.theory.runner_type_catalog import RUNNER_TYPES


def test_重みはレースごとに合計をそろえ_全体の平均は1():
    weights = RaceWeights().of(pd.Series(["a", "a", "a", "a", "b", "b"]))
    assert weights.iloc[0] * 4 == pytest.approx(weights.iloc[4] * 2)
    assert weights.mean() == pytest.approx(1.0)


def test_並べ替えの点数はレースの人気薄の市場合計を分ける():
    probability = RankProbability(0.5).of(pd.Series(["r", "r"]), np.array([0.0, np.log(3.0)]), pd.Series([0.1, 0.1]))
    assert probability.sum() == pytest.approx(0.1)          # 市場合計 0.2 × 0.5
    assert probability[1] == pytest.approx(0.075)
    assert RankProbability.scale_of(pd.Series([1, 0, 0]), pd.Series([0.5, 0.5, 1.0])) == pytest.approx(0.5)


def test_並べ替えの組はレースごとの行の数():
    ids = pd.DataFrame({"レースID": ["a", "a", "b", "c", "c", "c"]})
    data = LongshotData(ids, ids, ids["レースID"], ids["レースID"], ids["レースID"], ids["レースID"], ())
    assert RankLightGbm._groups(data).tolist() == [2, 1, 3]


def test_人気薄の確率を置き換え_ほかの馬は残りに縮める():
    current = pd.DataFrame({
        "race_id": ["r"] * 3, "race_date": ["2024-01-01"] * 3, "horse_id": ["h1", "h2", "h3"], "horse_no": [1, 2, 3],
        "probability": [0.6, 0.3, 0.1], "fold": ["f"] * 3, "period": ["テスト"] * 3, "segment": ["全体"] * 3,
    })
    longshot = pd.DataFrame({"レースID": ["r"], "馬番": [3], "確率": [0.2], "人気": [12.0]})
    combined = CombinedWinShare().combine(current, longshot).set_index("馬番")["確率"]
    assert combined[3] == pytest.approx(0.2)
    assert combined[1] == pytest.approx(0.6 / 0.9 * 0.8)
    assert combined.sum() == pytest.approx(1.0)


def test_確かめの表は人気薄の行だけで_勝ち馬の順位を数える():
    current = pd.DataFrame({"race_id": ["r"] * 3, "horse_no": [1, 2, 3], "probability": [0.8, 0.15, 0.05]})
    predicted = pd.DataFrame({
        "レースID": ["r"] * 3, "馬番": [1, 2, 3], "確率": [0.5, 0.01, 0.03], "開催日": pd.to_datetime(["2024-01-01"] * 3),
        "人気": [1.0, 10.0, 11.0], "1着": [0, 0, 1], "オッズから見た勝率": [0.8, 0.12, 0.08],
    })
    frame = EvaluationFrame().build(current, {"新": predicted})
    assert frame["horse_no"].tolist() == [2, 3]
    table = OrderingCaptureTable().build(frame, [MARKET, CURRENT, "新"], "t")
    rows = {row[0]: row[1] for row in table.rows}
    assert rows[MARKET] == "0.0%" and rows[CURRENT] == "0.0%" and rows["新"] == "100.0%"


def test_型の材料はハンデ戦だけ斤量差を持ち_型の真偽を数にする():
    base = {
        "race_id": ["r", "s"], "horse_no": [1.0, 2.0], "weight_type": ["ハンデ", "定量"], "front_places_before": [3.0, 0.0],
        "back_places_before": [1.0, 0.0], "recent_front_places": [2.0, 0.0], "recent_back_places": [0.0, 0.0],
        "prev_style": ["差し", None], "style_before": ["先行", "追込"], "lead_candidates": [1.0, 3.0], "best_placed_class": [6.0, None],
        "best_win_class": [4.0, None], "class_order": [5.0, 3.0], "distance_m": [1600.0, 1200.0], "prev_distance_m": [2000.0, 1200.0],
        "prev_condition": ["重", "良"], "condition": ["良", "良"], "prev_class_order": [6.0, 3.0], "carried_gap": [-1.5, 0.5],
        "jockey_rate": [0.1, 0.05], "prev_jockey_rate": [0.05, 0.05], "longshot_market": [0.12, 0.02], "favorite_odds": [4.5, 1.8],
        **{rule.name: [True, False] for rule in RUNNER_TYPES},
    }
    features = TypeFeatures().build(pd.DataFrame(base))
    assert list(features.columns) == ["レースID", "馬番", *COLUMNS]
    first, second = features.iloc[0], features.iloc[1]
    assert first["型_ハンデの斤量差"] == -1.5 and pd.isna(second["型_ハンデの斤量差"])
    assert first["型_前と後ろの3着内の差"] == 2.0 and first["型_楽に前へ行ける"] == 1.0 and second["型_楽に前へ行ける"] == 0.0
    assert first["型_前走との距離の差"] == 400.0 and first["型_前走から馬場が替わった"] == 1.0
    assert first["型_A"] == 1.0 and second["型_G"] == 0.0
