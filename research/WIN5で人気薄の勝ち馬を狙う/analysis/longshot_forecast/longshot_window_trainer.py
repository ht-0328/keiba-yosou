"""1つの区切り・1つの作り方で、LightGBM と CatBoost を学び、テストの半年の人気薄の1着の確率を返す。"""

from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

from yosou.shared.setting import HyperparameterSettings

from 既存モデルの改善.analysis.windows.test_window import TestWindow

from .longshot_data import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, LongshotData
from .longshot_variant import LONGSHOT_FROM, LongshotVariant
from .race_weights import RaceWeights
from .rank_catboost import RankCatBoost
from .rank_lightgbm import RankLightGbm
from .rank_probability import RankProbability
from .weighted_catboost import WeightedCatBoost
from .weighted_lightgbm import WeightedLightGbm

#: 予測の表の列（研究「既存モデルの改善」の予測の表と同じ名前。道具「印の成績」の ``PredictionFile`` で読める）。
WINDOW, PART, SEGMENT, PROBABILITY, POPULARITY = "区切り", "期間", "区分", "確率", "人気"
#: 確かめに使う列（1着か・オッズから見た勝率）。
WON, MARKET = "1着", "オッズから見た勝率"
TEST, WHOLE = "テスト", "全体"


class LongshotWindowTrainer:
    """学習 = 検証の始まりより前、検証 = テストの直前の半年（木を足すのを止める判断だけに使う）、テスト = その半年。

    二値分類は、レースごとに重みの合計をそろえて学ぶ。並べ替えは、学習と検証を人気薄（10番人気以下）が勝ったレースの
    人気薄の行だけにして学び、テストでは全部の人気薄の行に点数を付けて確率に直す（``RankProbability``）。"""

    def __init__(self, settings: HyperparameterSettings, threads: int) -> None:
        self._settings = settings
        self._threads = threads

    def run(self, data: LongshotData, window: TestWindow, variant: LongshotVariant) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        test = data.between(pd.Timestamp(window.test_first_day), pd.Timestamp(window.test_last_day))
        started = time.perf_counter()
        members, train = self.fit(data, window, variant)
        seconds = round(time.perf_counter() - started, 1)
        frame = self._frame(test, self.probabilities(members, train, test, variant), window.name)
        log = [{"区切り": window.name, "作り方": variant.label, "モデル": member.name, "木の数": member.tree_count,
                "学習の行数": len(train), "秒": seconds} for member in members]
        print(f"{variant.key} / {window.name}: 学習 {len(train):,}行・テスト {len(test):,}行・{seconds:.0f}秒", file=sys.stderr, flush=True)
        return frame, log

    def fit(self, data: LongshotData, window: TestWindow, variant: LongshotVariant) -> tuple[list, LongshotData]:
        """（学んだ2つのモデル, 学習の期間の行）。テストの行は使わない。並べ替えは、学習の期間の行のうち人気薄が勝ったレースだけで学ぶが、
        返すのは学習の期間の人気薄の全部の行（点数を確率に直す倍率は、人気薄の全部の行から出すため）。"""
        train = data.between(None, pd.Timestamp(window.valid_first_day) - pd.Timedelta(days=1))
        valid = data.between(pd.Timestamp(window.valid_first_day), pd.Timestamp(window.test_first_day) - pd.Timedelta(days=1))
        fitted_train, fitted_valid = (self._won_races(train), self._won_races(valid)) if variant.ranker else (train, valid)
        members = [member.fit(fitted_train, fitted_valid, self._weights(fitted_train, variant), self._weights(fitted_valid, variant))
                   for member in self._members(variant)]
        return members, train.where(train.popularity >= LONGSHOT_FROM) if variant.ranker else train

    def probabilities(self, members: list, train: LongshotData, test: LongshotData, variant: LongshotVariant) -> dict[str, np.ndarray]:
        """モデルの名前 → ``test`` の各行の人気薄の1着の確率。"""
        return {member.name: self._probability(member, train, test, variant) for member in members}

    def _members(self, variant: LongshotVariant) -> list:
        if variant.ranker:
            return [RankLightGbm(self._settings.lightgbm, self._threads), RankCatBoost(self._settings.catboost, self._threads)]
        return [WeightedLightGbm(self._settings.lightgbm, self._threads), WeightedCatBoost(self._settings.catboost, self._threads)]

    @staticmethod
    def _weights(data: LongshotData, variant: LongshotVariant) -> np.ndarray:
        if variant.ranker or not variant.weighted:
            return np.ones(len(data))
        return RaceWeights().of(data.race_ids.reset_index(drop=True)).to_numpy()

    @staticmethod
    def _won_races(data: LongshotData) -> LongshotData:
        """人気薄（10番人気以下）が勝ったレースの、人気薄の行だけ。"""
        longshot = data.where(data.popularity >= LONGSHOT_FROM)
        won = longshot.label.groupby(longshot.race_ids.to_numpy()).transform("sum").to_numpy() > 0
        return longshot.where(won)

    @staticmethod
    def _probability(member, train: LongshotData, test: LongshotData, variant: LongshotVariant) -> np.ndarray:
        score = test.baseline.to_numpy() + member.raw(test)
        if not variant.ranker:
            return 1.0 / (1.0 + np.exp(-score))
        scale = RankProbability.scale_of(train.label, train.market)
        return RankProbability(scale).of(test.race_ids, score, test.market)

    @staticmethod
    def _frame(test: LongshotData, probabilities: dict[str, np.ndarray], window: str) -> pd.DataFrame:
        ids = test.ids[[RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO]].reset_index(drop=True)
        average = np.mean(np.stack(list(probabilities.values())), axis=0)
        return ids.assign(**probabilities, **{PROBABILITY: average, POPULARITY: test.popularity.to_numpy(),
                                              WON: test.label.to_numpy(), MARKET: test.market.to_numpy(),
                                              WINDOW: window, PART: TEST, SEGMENT: WHOLE})
