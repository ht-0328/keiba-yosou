"""複勝・ワイドの払戻の倍率を、最低オッズから見積もる。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

#: 見積もりを分ける、最低オッズの区切り（帯は「左より大きく、右以下」）。
BANDS: tuple[float, ...] = (0.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0, 1e9)


class PlacePriceEstimator:
    """複勝・ワイドで実際に受け取る払戻の倍率を、最低オッズから見積もる（既存モデルの修正計画の 2「馬を選ぶ基準」）。

    複勝・ワイドの払戻は、一緒に来た馬の組み合わせで変わるので、買う時点では最低〜最高の幅しか分からない。
    過去の当たった買い目から「払戻 ÷（100 × 最低オッズ）」の平均を最低オッズの帯ごとに求め、それを最低オッズに掛けて
    見込みの倍率にする。例: 最低オッズ 2.4倍の帯の平均が 1.18 なら、見込みの倍率は 2.4 × 1.18 ≒ 2.83。
    推定には、評価する期間より前の期間だけを使う。当たりの無かった帯は、全体の平均を使う。
    """

    def __init__(self) -> None:
        self._factors: np.ndarray | None = None

    def fit(self, lowest_odds: pd.Series, payout_yen: pd.Series) -> PlacePriceEstimator:
        """当たった買い目（払戻 > 0）の最低オッズと払戻（100円あたり）から、帯ごとの倍率を決める。"""
        odds = pd.to_numeric(lowest_odds, errors="coerce")
        payout = pd.to_numeric(payout_yen, errors="coerce").fillna(0.0)
        hit = (payout > 0) & (odds > 0)
        ratio = (payout[hit] / (100.0 * odds[hit])).to_numpy()
        band = self._band_of(odds[hit].to_numpy())
        fallback = float(ratio.mean()) if len(ratio) else 1.0
        self._factors = np.array([self._mean_or(ratio[band == position], fallback) for position in range(len(BANDS) - 1)])
        return self

    def estimate(self, lowest_odds: pd.Series) -> pd.Series:
        """見込みの払戻の倍率（最低オッズ × 帯ごとの倍率）。最低オッズが無ければ欠損値。"""
        odds = pd.to_numeric(lowest_odds, errors="coerce")
        return pd.Series(self.estimate_array(odds.to_numpy(dtype="float64")), index=lowest_odds.index)

    def estimate_array(self, lowest_odds: np.ndarray) -> np.ndarray:
        """``estimate`` の配列版（1レースの買い目をまとめて見積もるときに使う）。"""
        if self._factors is None:
            raise RuntimeError("まだ推定していません（fit を先に呼んでください）")
        return lowest_odds * self._factors[self._band_of(lowest_odds)]

    def multipliers(self) -> dict[str, float]:
        """帯ごとの倍率（表に出す形）。"""
        if self._factors is None:
            return {}
        return {f"{BANDS[position]:g}〜{BANDS[position + 1]:g}倍": round(float(value), 3)
                for position, value in enumerate(self._factors)}

    def state(self) -> dict[str, Any]:
        """保存する形（帯の区切りと帯ごとの倍率）。"""
        if self._factors is None:
            raise RuntimeError("まだ推定していません（fit を先に呼んでください）")
        return {"bands": list(BANDS), "factors": [float(value) for value in self._factors]}

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> PlacePriceEstimator:
        """``state()`` で書いた形から作り直す。帯の区切りが今のものと違えば ``ValueError``。"""
        if tuple(float(value) for value in state["bands"]) != BANDS:
            raise ValueError("複勝の見込みの倍率の帯の区切りが、保存したときと違います。train で学習し直してください。")
        estimator = cls()
        estimator._factors = np.array(state["factors"], dtype="float64")
        return estimator

    def _band_of(self, odds: np.ndarray) -> np.ndarray:
        """最低オッズの帯の番号（0 から）。"""
        return np.clip(np.digitize(odds, BANDS, right=True) - 1, 0, len(BANDS) - 2)

    def _mean_or(self, values: np.ndarray, fallback: float) -> float:
        return float(values.mean()) if len(values) else fallback
