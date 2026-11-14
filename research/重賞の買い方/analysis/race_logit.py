"""レースの中の組の確率（条件付きロジット）を、重賞だけで学んで出す（docs/05 の 2）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


class RaceLogit:
    """表（race_id の順に並んだ 1行 = 1組。列 race_id・y・hit と、もとの対数の列）から、組の確率 ∝ exp(重み · もと) をレースの中で合計 1 にした値を出す。

    ``cross_fitted`` は、選ぶ期間の年は「その年を抜いた選ぶ期間」で学んだ重み、確かめる期間は選ぶ期間の全部で学んだ重みで出す（学びに使った年を数えない）。
    """

    def cross_fitted(self, table: pd.DataFrame, names: list[str], select_years: range, confirm_years: range) -> np.ndarray:
        result = np.full(len(table), np.nan)
        for year in select_years:
            train = table["y"].isin(select_years) & (table["y"] != year)
            result[(table["y"] == year).to_numpy()] = self._predict(table[table["y"] == year], names, self.fit(table[train], names))
        late = table["y"].isin(confirm_years)
        result[late.to_numpy()] = self._predict(table[late], names, self.fit(table[table["y"].isin(select_years)], names))
        return result

    def fit(self, table: pd.DataFrame, names: list[str]) -> np.ndarray:
        features, hit, starts = table[names].to_numpy(dtype=float), table["hit"].to_numpy(dtype=float), self._starts(table)
        first = np.zeros(len(names))
        first[0] = 1.0

        def loss(weights: np.ndarray) -> tuple[float, np.ndarray]:
            score = features @ weights
            probability, log_total = self._softmax(score, starts)
            return -float((hit * (score - log_total)).sum()), -(features.T @ (hit - probability))

        return minimize(loss, first, jac=True, method="L-BFGS-B").x

    def probability(self, table: pd.DataFrame, score: np.ndarray) -> np.ndarray:
        """重みを掛けた値 ``score`` から、レースの中で合計 1 の確率（欠損のあるレースは欠損）。"""
        frame = pd.DataFrame({"race_id": table["race_id"].to_numpy(), "score": score})
        exponent = np.exp(frame["score"] - frame.groupby("race_id")["score"].transform("max"))
        return (exponent / exponent.groupby(frame["race_id"]).transform("sum")).to_numpy()

    def _predict(self, table: pd.DataFrame, names: list[str], weights: np.ndarray) -> np.ndarray:
        return self._softmax(table[names].to_numpy(dtype=float) @ weights, self._starts(table))[0]

    @staticmethod
    def _starts(table: pd.DataFrame) -> np.ndarray:
        ids = table["race_id"].to_numpy()
        return np.flatnonzero(np.r_[True, ids[1:] != ids[:-1]])

    @staticmethod
    def _softmax(score: np.ndarray, starts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        sizes = np.diff(np.r_[starts, len(score)])
        top = np.repeat(np.maximum.reduceat(score, starts), sizes)
        exponent = np.exp(score - top)
        log_total = top + np.log(np.repeat(np.add.reduceat(exponent, starts), sizes))
        return np.exp(score - log_total), log_total
