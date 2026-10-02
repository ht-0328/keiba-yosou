"""レースの中で見る指標（レースごとのログ損失・順位相関など）を、まとめて計算する。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: ログを取るときに 0 にならないようにする下限。
_FLOOR = 1e-12


class RaceMetrics:
    """1行 = 1頭の表から、レースの中で見る指標を出す（設計書 16 の 2）。レースごとに関数を呼ぶと遅いので、まとめて計算する。"""

    def race_log_loss(self, probability: pd.Series, is_answer: pd.Series) -> float:
        """正解の馬（先頭・1着）に付けた確率 p の ``−log(p)`` の平均（正解が1頭のレースだけ）。"""
        answers = is_answer == 1
        return float(-np.log(np.clip(probability[answers].to_numpy(dtype="float64"), _FLOOR, 1.0)).mean())

    def top_hit_rate(self, probability: pd.Series, race: pd.Series, is_answer: pd.Series) -> float:
        """確率がいちばん高い馬が正解だったレースの割合。"""
        best = probability.groupby(race).transform("max")
        top = probability.eq(best) & probability.notna()
        first_top = top & ~top.groupby(race).cumsum().gt(1)
        return float(is_answer[first_top].eq(1).mean())

    def rank_correlation(self, predicted: pd.Series, actual: pd.Series, race: pd.Series) -> float:
        """レースの中の、予測の順と実際の順の相関（スピアマンの順位相関）を、レースで平均した値。"""
        usable = predicted.notna() & actual.notna()
        race, predicted, actual = race[usable], predicted[usable], actual[usable]
        x = predicted.groupby(race).rank()
        y = actual.groupby(race).rank()
        x = x - x.groupby(race).transform("mean")
        y = y - y.groupby(race).transform("mean")
        covariance = (x * y).groupby(race).sum()
        spread = np.sqrt((x * x).groupby(race).sum() * (y * y).groupby(race).sum())
        return float((covariance / spread.where(spread > 0)).mean())

    def multiclass_log_loss(self, probabilities: np.ndarray, labels: np.ndarray) -> float:
        """3つの確率が正解から外れた大きさ（1行ずつの ``−log(正解のクラスの確率)`` の平均）。"""
        picked = probabilities[np.arange(len(labels)), labels.astype(int)]
        return float(-np.log(np.clip(picked, _FLOOR, 1.0)).mean())
