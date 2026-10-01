"""複勝・ワイドの払戻の倍率を、最低オッズ（と、渡されれば最高オッズ）から見積もる。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

#: 見積もりを分ける、最低オッズの区切り（帯は「左より大きく、右以下」）。
BANDS: tuple[float, ...] = (0.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0, 1e9)
#: 見積もりを直す、オッズの幅（最高オッズ ÷ 最低オッズ）の区切り（帯は「左より大きく、右以下」）。
SPREAD_BANDS: tuple[float, ...] = (1.0, 1.4, 1.5, 1.6, 1.7, 1.85, 2.0, 2.5, 1e9)


class PlacePriceEstimator:
    """複勝・ワイドで実際に受け取る払戻の倍率を、最低オッズから見積もる（既存モデルの修正計画の 2「馬を選ぶ基準」）。

    複勝・ワイドの払戻は、一緒に来た馬の組み合わせで変わるので、買う時点では最低〜最高の幅しか分からない。
    過去の当たった買い目から「払戻 ÷（100 × 最低オッズ）」の平均を最低オッズの帯ごとに求め、それを最低オッズに掛けて
    見込みの倍率にする。例: 最低オッズ 2.4倍の帯の平均が 1.18 なら、見込みの倍率は 2.4 × 1.18 ≒ 2.83。
    推定には、評価する期間より前の期間だけを使う。当たりの無かった帯は、全体の平均を使う。

    **最高オッズも渡すと、オッズの幅（最高 ÷ 最低）でも直す**（穴馬の設計書 15 の 18）。同じ最低オッズでも、幅の狭い馬は
    払戻が最低オッズ寄りに、幅の広い馬は高めに出るので、最低オッズの帯だけで見積もると、幅の狭い馬を高めに見積もる。
    そこで、当たった買い目の「払戻 ÷（100 × 最低オッズ × 帯の倍率）」の平均を幅の帯ごとに求め、それも掛ける。
    例: 上の馬の幅が 1.45 倍で、その幅の帯の倍率が 0.93 なら、見込みの倍率は 2.83 × 0.93 ≒ 2.63。
    最高オッズを渡さずに学んだもの（前の版で保存したものを含む）と、最高オッズの無い馬は、幅で直さない。
    """

    def __init__(self) -> None:
        self._factors: np.ndarray | None = None
        self._spread_factors: np.ndarray | None = None

    def fit(self, lowest_odds: pd.Series, payout_yen: pd.Series,
            highest_odds: pd.Series | None = None) -> PlacePriceEstimator:
        """当たった買い目（払戻 > 0）の最低オッズと払戻（100円あたり）から、帯ごとの倍率を決める。

        ``highest_odds``（最高オッズ）を渡すと、幅の帯ごとの直しの倍率も決める。
        """
        odds = pd.to_numeric(lowest_odds, errors="coerce")
        payout = pd.to_numeric(payout_yen, errors="coerce").fillna(0.0)
        hit = (payout > 0) & (odds > 0)
        ratio = (payout[hit] / (100.0 * odds[hit])).to_numpy()
        band = self._band_of(odds[hit].to_numpy())
        fallback = float(ratio.mean()) if len(ratio) else 1.0
        self._factors = np.array([self._mean_or(ratio[band == position], fallback) for position in range(len(BANDS) - 1)])
        self._spread_factors = None if highest_odds is None else self._fit_spread(odds[hit], payout[hit], highest_odds[hit])
        return self

    def estimate(self, lowest_odds: pd.Series, highest_odds: pd.Series | None = None) -> pd.Series:
        """見込みの払戻の倍率（最低オッズ × 帯ごとの倍率。幅で直すときは × 幅の帯の倍率）。最低オッズが無ければ欠損値。"""
        odds = pd.to_numeric(lowest_odds, errors="coerce").to_numpy(dtype="float64")
        highest = None if highest_odds is None else pd.to_numeric(highest_odds, errors="coerce").to_numpy(dtype="float64")
        return pd.Series(self.estimate_array(odds, highest), index=lowest_odds.index)

    def estimate_array(self, lowest_odds: np.ndarray, highest_odds: np.ndarray | None = None) -> np.ndarray:
        """``estimate`` の配列版（1レースの買い目をまとめて見積もるときに使う）。"""
        if self._factors is None:
            raise RuntimeError("まだ推定していません（fit を先に呼んでください）")
        return lowest_odds * self._factors[self._band_of(lowest_odds)] * self._spread_multiplier(lowest_odds, highest_odds)

    def multipliers(self) -> dict[str, float]:
        """帯ごとの倍率（表に出す形）。"""
        if self._factors is None:
            return {}
        return {f"{BANDS[position]:g}〜{BANDS[position + 1]:g}倍": round(float(value), 3)
                for position, value in enumerate(self._factors)}

    def spread_multipliers(self) -> dict[str, float]:
        """幅の帯ごとの直しの倍率（表に出す形）。幅で直さないなら空。"""
        if self._spread_factors is None:
            return {}
        return {f"{SPREAD_BANDS[position]:g}〜{SPREAD_BANDS[position + 1]:g}": round(float(value), 3)
                for position, value in enumerate(self._spread_factors)}

    def state(self) -> dict[str, Any]:
        """保存する形（帯の区切りと帯ごとの倍率。幅で直すときは、幅の帯の区切りと倍率も）。"""
        if self._factors is None:
            raise RuntimeError("まだ推定していません（fit を先に呼んでください）")
        state: dict[str, Any] = {"bands": list(BANDS), "factors": [float(value) for value in self._factors]}
        if self._spread_factors is None:
            return state
        return {**state, "spread_bands": list(SPREAD_BANDS),
                "spread_factors": [float(value) for value in self._spread_factors]}

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> PlacePriceEstimator:
        """``state()`` で書いた形から作り直す。帯の区切りが今のものと違えば ``ValueError``。幅の倍率が無ければ幅で直さない。"""
        if tuple(float(value) for value in state["bands"]) != BANDS:
            raise ValueError("複勝の見込みの倍率の帯の区切りが、保存したときと違います。train で学習し直してください。")
        if "spread_factors" in state and tuple(float(value) for value in state["spread_bands"]) != SPREAD_BANDS:
            raise ValueError("複勝の見込みの倍率の幅の帯の区切りが、保存したときと違います。train で学習し直してください。")
        estimator = cls()
        estimator._factors = np.array(state["factors"], dtype="float64")
        spread = state.get("spread_factors")
        estimator._spread_factors = None if spread is None else np.array(spread, dtype="float64")
        return estimator

    def _fit_spread(self, odds: pd.Series, payout: pd.Series, highest_odds: pd.Series) -> np.ndarray:
        """当たった買い目の「払戻 ÷ 帯の倍率で見積もった払戻」の平均を、幅の帯ごとに出す。当たりの無い帯は 1。"""
        highest = pd.to_numeric(highest_odds, errors="coerce").to_numpy(dtype="float64")
        lowest = odds.to_numpy(dtype="float64")
        known = np.isfinite(highest) & (highest >= lowest)
        residual = (payout.to_numpy(dtype="float64") / (100.0 * lowest * self._factors[self._band_of(lowest)]))[known]
        band = self._spread_band_of(lowest[known], highest[known])
        return np.array([self._mean_or(residual[band == position], 1.0) for position in range(len(SPREAD_BANDS) - 1)])

    def _spread_multiplier(self, lowest_odds: np.ndarray, highest_odds: np.ndarray | None) -> np.ndarray:
        """幅の帯の倍率。幅で直さないとき・最高オッズの無い馬は 1。"""
        if self._spread_factors is None or highest_odds is None:
            return np.ones(len(lowest_odds))
        known = np.isfinite(highest_odds) & (highest_odds >= lowest_odds)
        factors = self._spread_factors[self._spread_band_of(lowest_odds, np.where(known, highest_odds, lowest_odds))]
        return np.where(known, factors, 1.0)

    def _band_of(self, odds: np.ndarray) -> np.ndarray:
        """最低オッズの帯の番号（0 から）。"""
        return np.clip(np.digitize(odds, BANDS, right=True) - 1, 0, len(BANDS) - 2)

    def _spread_band_of(self, lowest_odds: np.ndarray, highest_odds: np.ndarray) -> np.ndarray:
        """オッズの幅（最高 ÷ 最低）の帯の番号（0 から）。"""
        with np.errstate(divide="ignore", invalid="ignore"):
            spread = highest_odds / lowest_odds
        return np.clip(np.digitize(spread, SPREAD_BANDS, right=True) - 1, 0, len(SPREAD_BANDS) - 2)

    def _mean_or(self, values: np.ndarray, fallback: float) -> float:
        return float(values.mean()) if len(values) else fallback
