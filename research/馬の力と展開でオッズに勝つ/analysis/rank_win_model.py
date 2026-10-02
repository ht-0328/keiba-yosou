"""同じレースの馬どうしを比べて学ぶ（順位の学習）で、1着になる確率を出す。"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

#: 早期終了まで待つ本数。
_PATIENCE = 100


class RankWinModel:
    """LightGBM の順位の学習（lambdarank）で、レースの中の並びを学ぶ。

    答えの列は、1着 3・2着 2・3着 1・それ以外 0（1着だけより多くの情報を使う）。
    出てきた点数を、レースの中で exp(点数 ÷ 温度) の割合にして確率にする。温度は検証の年のログ損失が
    いちばん小さくなる値にする（点数の大きさには確率としての意味が無いため）。
    ``table`` は race_id の順に並んでいること。
    """

    def __init__(self, learning_rate: float = 0.05) -> None:
        self._learning_rate = learning_rate
        self._temperature = 1.0

    def fit(self, train: pd.DataFrame, valid: pd.DataFrame, features: list[str]) -> RankWinModel:
        self._features = features
        self._model = lgb.LGBMRanker(objective="lambdarank", n_estimators=3000, learning_rate=self._learning_rate,
                                     num_leaves=63, min_child_samples=200, subsample=0.8, subsample_freq=1,
                                     colsample_bytree=0.7, verbose=-1, lambdarank_truncation_level=5)
        self._model.fit(train[features], self._relevance(train), group=self._groups(train),
                        eval_set=[(valid[features], self._relevance(valid))], eval_group=[self._groups(valid)],
                        eval_at=[1, 3], callbacks=[lgb.early_stopping(_PATIENCE, verbose=False)])
        self._temperature = self._fit_temperature(valid)
        return self

    def predict(self, table: pd.DataFrame) -> np.ndarray:
        return self._softmax(self._model.predict(table[self._features]), table["race_id"].to_numpy(),
                             self._temperature)

    def importance(self) -> pd.Series:
        return pd.Series(self._model.booster_.feature_importance("gain"),
                         index=self._features).sort_values(ascending=False)

    def _relevance(self, table: pd.DataFrame) -> np.ndarray:
        finish = pd.to_numeric(table["finish"], errors="coerce").fillna(99).to_numpy()
        return np.where(finish <= 3, 4 - finish, 0).astype(int)

    def _groups(self, table: pd.DataFrame) -> np.ndarray:
        return table.groupby("race_id", sort=False).size().to_numpy()

    def _fit_temperature(self, valid: pd.DataFrame) -> float:
        score = self._model.predict(valid[self._features])
        race = valid["race_id"].to_numpy()
        won = valid["won"].to_numpy() == 1

        def loss(temperature: float) -> float:
            probability = self._softmax(score, race, temperature)
            return float(-np.log(np.clip(probability[won], 1e-9, None)).mean())

        return float(minimize_scalar(loss, bounds=(0.05, 5.0), method="bounded").x)

    def _softmax(self, score: np.ndarray, race: np.ndarray, temperature: float) -> np.ndarray:
        scaled = pd.Series(score / temperature)
        scaled = scaled - scaled.groupby(race).transform("max").to_numpy()
        exponent = np.exp(scaled.to_numpy())
        return exponent / pd.Series(exponent).groupby(race).transform("sum").to_numpy()
