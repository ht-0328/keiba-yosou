"""1つの区切り・1つの作り方で、LightGBM と CatBoost を学び、検証とテストの半年の、展開の型ごとの確率と混ぜた確率を返す。"""

from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

from yosou.shared.setting import HyperparameterSettings

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, LongshotData
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.weighted_catboost import WeightedCatBoost
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.weighted_lightgbm import WeightedLightGbm
from 既存モデルの改善.analysis.windows.test_window import TestWindow

from .scenario_materials import PACE
from .scenario_predictor import ScenarioPredictor
from .scenario_variant import ScenarioVariant
from .scenario_weights import ScenarioWeights

#: 予測の表の列（道具「印の成績」の ``PredictionFile`` が読む名前と、確かめに使う列）。
WINDOW, PART, SEGMENT, PROBABILITY, POPULARITY = "区切り", "期間", "区分", "確率", "人気"
LABEL, MARKET, ACTUAL_PACE = "目的変数", "オッズから見た率", "実際の展開の型"
SCENARIO_COLUMNS = ("確率_スロー", "確率_平均", "確率_ハイ")
VALID, TEST, WHOLE = "検証", "テスト", "全体"


class ScenarioWindowTrainer:
    """学習 = 検証の始まりより前、検証 = テストの直前の半年（木を足すのを止める判断と、道具「印の成績」が危険の線を決めるのに使う）、
    テスト = その半年。重みは付けない（全頭を同じ重みで学ぶ）。混ぜる重みの予想が無い行は、学習の期間の結果のペースの割合で混ぜる。"""

    def __init__(self, settings: HyperparameterSettings, threads: int, lightgbm_class: type = WeightedLightGbm) -> None:
        self._settings = settings
        self._threads = threads
        self._lightgbm_class = lightgbm_class

    def fit(self, data: LongshotData, window: TestWindow) -> tuple[list, ScenarioWeights, int]:
        """（学んだ2つのモデル, 混ぜる重み, 学習の行数）。学習と検証の行だけを使う。"""
        train = data.between(None, pd.Timestamp(window.valid_first_day) - pd.Timedelta(days=1))
        valid = data.between(pd.Timestamp(window.valid_first_day), pd.Timestamp(window.test_first_day) - pd.Timedelta(days=1))
        ones_train, ones_valid = np.ones(len(train)), np.ones(len(valid))
        members = [self._lightgbm_class(self._settings.lightgbm, self._threads).fit(train, valid, ones_train, ones_valid),
                   WeightedCatBoost(self._settings.catboost, self._threads).fit(train, valid, ones_train, ones_valid)]
        prior = ScenarioWeights.prior_of(train.features[PACE]) if PACE in train.features else np.full(3, 1 / 3)
        return members, ScenarioWeights(prior), len(train)

    def run(self, data: LongshotData, window: TestWindow, variant: ScenarioVariant) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        valid = data.between(pd.Timestamp(window.valid_first_day), pd.Timestamp(window.test_first_day) - pd.Timedelta(days=1))
        test = data.between(pd.Timestamp(window.test_first_day), pd.Timestamp(window.test_last_day))
        started = time.perf_counter()
        members, weights, train_rows = self.fit(data, window)
        frames = [self._frame(part, members, weights, window.name, label) for part, label in ((valid, VALID), (test, TEST))]
        seconds = round(time.perf_counter() - started, 1)
        log = [{"区切り": window.name, "作り方": variant.label, "モデル": member.name, "木の数": member.tree_count,
                "学習の行数": train_rows, "秒": seconds} for member in members]
        print(f"{variant.key} / {window.name}: 学習 {train_rows:,}行・テスト {len(test):,}行・{seconds:.0f}秒", file=sys.stderr, flush=True)
        return pd.concat(frames, ignore_index=True), log

    @staticmethod
    def _frame(data: LongshotData, members: list, weights: ScenarioWeights, window: str, part: str) -> pd.DataFrame:
        ids = data.ids[[RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO]].reset_index(drop=True)
        scenarios, mixed = [], {}
        for member in members:
            predictor = ScenarioPredictor(member, weights)
            scenario = predictor.by_scenario(data)
            scenarios.append(scenario)
            mixed[member.name] = predictor.mixed(data, scenario)
        average = np.mean(np.stack(scenarios), axis=0)
        actual = data.features[PACE].to_numpy() if PACE in data.features else np.full(len(data), np.nan)
        return ids.assign(**mixed, **{PROBABILITY: np.mean(np.stack(list(mixed.values())), axis=0)},
                          **{name: average[:, index] for index, name in enumerate(SCENARIO_COLUMNS)},
                          **{POPULARITY: data.popularity.to_numpy(), LABEL: data.label.to_numpy(), MARKET: data.market.to_numpy(),
                             ACTUAL_PACE: actual, WINDOW: window, PART: part, SEGMENT: WHOLE})
