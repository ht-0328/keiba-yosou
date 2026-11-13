"""段3 の予想の部品（その日の先のレースの傾き・材料・混ぜる重み・展開の型ごとの予測・区切りごとの学び）を、架空の値で確かめる。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest
import pandas as pd

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH
from yosou.shared.setting import HyperparameterSettings

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import LongshotData
from 既存モデルの改善.analysis.windows.test_window import TestWindow
from 超荒れの展開と適性から大穴を当てる.analysis.enrichment.runner_enrichment import RunnerEnrichment, SideTables
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.prior_race_bias import PriorRaceBias
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_materials import FORECAST, PACE, ScenarioMaterials
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_predictor import ScenarioPredictor
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_variant import ScenarioVariant
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_weights import ScenarioWeights
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_window_trainer import (PART, PROBABILITY, SCENARIO_COLUMNS,
                                                                                   ScenarioWindowTrainer)

from .frames import history, side_tables


def test_先のレースの傾きは同じ日_同じ競馬場_同じ芝ダの前のレースだけの平均():
    slopes = pd.DataFrame({
        "race_id": ["a1", "a2", "a3", "b1"], "race_date": ["2024-01-01"] * 4, "venue_code": ["06", "06", "06", "06"],
        "surface": ["芝", "芝", "芝", "ダート"], "race_no": [1, 2, 3, 2], "内の傾き": [0.2, np.nan, 0.4, 0.9], "前の傾き": [0.1, 0.3, 0.5, 0.0],
    })
    result = PriorRaceBias().of(slopes).set_index("race_id")
    assert pd.isna(result.loc["a1", "prior_inner"])               # その日の最初のレース
    assert result.loc["a2", "prior_inner"] == pytest.approx(0.2)
    assert result.loc["a3", "prior_inner"] == pytest.approx(0.2)              # 2レース目は傾きが無いので数えない
    assert result.loc["a3", "prior_front"] == pytest.approx(0.2)  # (0.1 + 0.3) ÷ 2
    assert pd.isna(result.loc["b1", "prior_inner"])               # ダートは別に数える


def test_材料は展開の型を数にし_当日だけ傾きと体重比を足す():
    runners = RunnerEnrichment(date(2024, 1, 1)).build(history(), SideTables(**side_tables()))
    runners = runners.assign(prior_inner=0.2, prior_front=0.1)
    day_before = ScenarioMaterials(race_day=False).build(runners)
    race_day = ScenarioMaterials(race_day=True).build(runners)
    assert "先のレースの内の傾き" not in day_before and "先のレースの内の傾き" in race_day
    last = race_day.loc[race_day["race_id"] == "2024040106010101"].set_index("horse_no")
    assert last.loc[1.0, PACE] == 2.0                              # ハイ
    assert last.loc[1.0, FORECAST[2]] == 0.6
    assert last.loc[1.0, "ハンデ戦か"] == 1.0
    assert last.loc[1.0, "内の傾き×内寄り"] == 0.2 * 0.5           # 馬番1は内の端（位置 0）
    assert set(ScenarioMaterials(race_day=True).columns) <= set(race_day.columns)


def test_混ぜる重みは予想が無ければ全体の割合():
    prior = ScenarioWeights.prior_of(pd.Series([0.0, 1.0, 1.0, 2.0, np.nan]))
    assert prior.tolist() == [0.25, 0.5, 0.25]
    weights = ScenarioWeights(prior).of(pd.DataFrame({"a": [0.2, np.nan], "b": [0.3, 0.1], "c": [0.5, 0.2]}))
    assert weights[0].tolist() == [0.2, 0.3, 0.5]
    assert weights[1].tolist() == [0.25, 0.5, 0.25]


class _PaceMember:
    """展開の型の値をそのままロジットの上げ下げにする、架空の学んだモデル。"""

    name = "架空"

    def raw(self, data: LongshotData) -> np.ndarray:
        return data.features[PACE].to_numpy(dtype=float)


def _data(rows: int = 4) -> LongshotData:
    features = pd.DataFrame({PACE: [2.0] * rows, FORECAST[0]: [1.0] * rows, FORECAST[1]: [0.0] * rows, FORECAST[2]: [0.0] * rows})
    ids = pd.DataFrame({"レースID": ["r"] * rows, "開催日": pd.to_datetime(["2024-01-01"] * rows), "馬ID": ["h"] * rows, "馬番": range(1, rows + 1)})
    zeros = pd.Series([0.0] * rows)
    return LongshotData(ids, features, pd.Series([0] * rows), zeros, zeros + 1, zeros + 0.5, ())


def test_展開の型ごとに予測して_予想のペースの確率で混ぜる():
    predictor = ScenarioPredictor(_PaceMember(), ScenarioWeights(np.full(3, 1 / 3)))
    data = _data()
    scenario = predictor.by_scenario(data)
    assert np.allclose(scenario[0], [0.5, 1 / (1 + np.exp(-1)), 1 / (1 + np.exp(-2))])
    assert np.allclose(predictor.mixed(data, scenario), 0.5)      # 予想はスロー 100%
    plain = _data()
    plain_features = plain.features.drop(columns=[PACE]).assign(**{PACE + "なし": 0.0})
    no_pace = LongshotData(plain.ids, plain_features, plain.label, plain.baseline, plain.popularity, plain.market, ())

    class _Flat:
        name = "平ら"

        def raw(self, data: LongshotData) -> np.ndarray:
            return np.zeros(len(data))

    assert np.allclose(ScenarioPredictor(_Flat(), ScenarioWeights(np.full(3, 1 / 3))).by_scenario(no_pace), 0.5)


def test_区切りごとの学びは検証とテストの行に展開の型ごとの確率を付ける():
    rng = np.random.default_rng(0)
    rows = 600
    days = pd.date_range("2023-01-01", periods=rows, freq="D")
    pace = rng.integers(0, 3, rows).astype(float)
    features = pd.DataFrame({PACE: pace, "x": rng.normal(size=rows), FORECAST[0]: 0.3, FORECAST[1]: 0.4, FORECAST[2]: 0.3})
    label = pd.Series((rng.random(rows) < 0.2 + 0.1 * pace).astype(int))
    ids = pd.DataFrame({"レースID": [f"r{i // 10}" for i in range(rows)], "開催日": days, "馬ID": "h", "馬番": [i % 10 + 1 for i in range(rows)]})
    baseline = pd.Series(np.full(rows, np.log(0.25 / 0.75)))
    data = LongshotData(ids, features, label, baseline, pd.Series(np.ones(rows)), pd.Series(np.full(rows, 0.25)), ())
    settings = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
    window = TestWindow("試し", date(2024, 1, 1), date(2024, 6, 1), date(2024, 8, 22))
    frame, log = ScenarioWindowTrainer(settings, 2).run(data, window, ScenarioVariant("t", "試し", "top3"))
    assert set(frame[PART]) == {"検証", "テスト"}
    assert frame[list(SCENARIO_COLUMNS)].notna().all().all()
    assert frame[PROBABILITY].between(0, 1).all()
    assert len(log) == 2
