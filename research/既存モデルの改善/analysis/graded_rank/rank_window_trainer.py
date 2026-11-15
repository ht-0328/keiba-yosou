"""1つの区切りで順位の予想を学び、テストの年の1着の確率と3着以内の確率を出す。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TOP3, WIN, TrainingData
from yosou.shared.setting import LightGbmSettings

from ..windows import TestWindow
from .plackett_luce import PlackettLuce
from .rank_model import RankModel


class RankWindowTrainer:
    """区切りの学習の期間で ``RankModel`` を学び、検証の期間で点数の効き具合（温度）を合わせ、テストの期間の確率を出す。

    使う列は ``columns``（今の本番の当日の3着以内の列）。オッズから作った基準は使わない（出発点はモデルの中でオッズから見た勝率の対数）。
    戻り値は（3着以内の予測の表, 1着の予測の表, 学習の記録の行）。予測の表は ``PredictionStore`` と同じ形（テストの期間の行だけ）。
    """

    def __init__(self, settings: LightGbmSettings, columns: Sequence[str]) -> None:
        self._settings = settings
        self._columns = list(columns)

    def run(self, data: TrainingData, window: TestWindow) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
        prepared = replace(data, features=data.features[self._columns], baseline=None)
        train, valid, test = window.train(prepared), window.valid(prepared), window.test(prepared)
        model = RankModel(self._settings).fit(train, valid)
        valid_groups, test_groups = _groups(valid), _groups(test)
        converter = PlackettLuce().fit(model.score(valid), valid_groups, valid.targets[WIN].to_numpy(dtype=float),
                                       valid.targets[TOP3].to_numpy(dtype=float))
        score = model.score(test)
        top3 = self._frame(test, converter.top3(score, test_groups), window.name)
        win = self._frame(test, converter.win(score, test_groups), window.name)
        log = {"区切り": window.name, "木の数": model.tree_count, "学習の行数": len(train),
               "1着の温度": round(converter.win_temperature, 4), "3着以内の温度": round(converter.top3_temperature, 4)}
        return top3, win, log

    def _frame(self, data: TrainingData, probability: np.ndarray, window: str) -> pd.DataFrame:
        ids = data.ids[[RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO]].reset_index(drop=True)
        return ids.assign(確率=probability, 区切り=window, 期間="テスト", 区分="全体")


def _groups(data: TrainingData) -> np.ndarray:
    return pd.factorize(data.ids[RACE_ID].astype(str))[0]
