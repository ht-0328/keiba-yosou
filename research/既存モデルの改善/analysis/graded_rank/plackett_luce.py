"""レースの中の点数から、1着の確率と3着以内の確率を出す（点数の効き具合は検証データで合わせる）。"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

_EPS = 1e-12


class PlackettLuce:
    """点数 s の馬の強さを exp(温度 × s) とし、1着の確率はレースの中で合計 1 にした値、3着以内の確率は、
    1着・2着・3着を順に残りの馬の中から強さの割合で選ぶ（Harville の式）。

    温度は、1着と3着以内で別々に、検証データのログ損失がいちばん小さくなる値にする（``fit``）。
    計算は、レースを行にした「頭数 × 頭数」の配列でまとめて行う（頭数の少ないレースは強さ 0 で埋める）。
    """

    def __init__(self) -> None:
        self.win_temperature = 1.0
        self.top3_temperature = 1.0

    def fit(self, score: np.ndarray, groups: np.ndarray, win: np.ndarray, top3: np.ndarray) -> PlackettLuce:
        self.win_temperature = self._best(lambda t: _logloss(win, self.win(score, groups, t)))
        self.top3_temperature = self._best(lambda t: _logloss(top3, self.top3(score, groups, t)))
        return self

    def win(self, score: np.ndarray, groups: np.ndarray, temperature: float | None = None) -> np.ndarray:
        strength, slots = self._padded(score, groups, self.win_temperature if temperature is None else temperature)
        return strength[slots]

    def top3(self, score: np.ndarray, groups: np.ndarray, temperature: float | None = None) -> np.ndarray:
        p, slots = self._padded(score, groups, self.top3_temperature if temperature is None else temperature)
        rest1 = np.clip(1.0 - p, _EPS, None)                                   # [レース, j]
        # 2着の項: p_i × Σ_{j≠i} p_j / (1 − p_j)
        ratio = p / rest1
        term2 = p * (ratio.sum(axis=1, keepdims=True) - ratio)
        # 3着の項: p_i × Σ_{j≠k, j,k≠i} p_j p_k / ((1 − p_j)(1 − p_j − p_k))
        rest2 = np.clip(1.0 - p[:, :, None] - p[:, None, :], _EPS, None)       # [レース, j, k]
        matrix = (p[:, :, None] * p[:, None, :]) / (rest1[:, :, None] * rest2)
        size = p.shape[1]
        matrix[:, np.arange(size), np.arange(size)] = 0.0
        total = matrix.sum(axis=(1, 2))[:, None]
        term3 = p * (total - matrix.sum(axis=2) - matrix.sum(axis=1))
        return np.clip(p + term2 + term3, 0.0, 1.0)[slots]

    def _padded(self, score: np.ndarray, groups: np.ndarray, temperature: float) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray]]:
        """（強さの割合 [レース, 頭], 行ごとの (レース, 頭) の位置）。"""
        order = np.argsort(groups, kind="stable")
        sorted_groups = groups[order]
        starts = np.searchsorted(sorted_groups, sorted_groups, side="left")
        position = np.empty_like(groups)
        position[order] = np.arange(len(groups)) - starts
        races = groups.max() + 1
        width = int(position.max()) + 1
        logits = np.full((races, width), -np.inf)
        logits[groups, position] = temperature * score
        logits -= logits.max(axis=1, keepdims=True)
        strength = np.exp(logits)
        strength /= strength.sum(axis=1, keepdims=True)
        return strength, (groups, position)

    @staticmethod
    def _best(loss) -> float:
        return float(minimize_scalar(loss, bounds=(0.05, 3.0), method="bounded").x)


def _logloss(label: np.ndarray, probability: np.ndarray) -> float:
    clipped = np.clip(probability, _EPS, 1 - _EPS)
    return float(-np.mean(label * np.log(clipped) + (1 - label) * np.log(1 - clipped)))
