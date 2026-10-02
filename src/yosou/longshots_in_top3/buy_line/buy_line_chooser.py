"""「買い」の線（複勝の期待値の線）を、検証期間の回収率で決める。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

#: 期待値の線の候補（研究「回収率100超」の複勝の線の候補と同じ）。
CANDIDATES: tuple[float, ...] = (1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4)
#: 線を選ぶのに要る、検証期間で買った点の数の下限。研究「回収率100超」の「1年あたり 300点以上」を、
#: 半年の検証期間に直した値（設計書 16 の 3）。
MIN_POINTS = 150
#: 線を選ぶのに要る、検証期間の回収率の下限（この値を超えること。1 で元返し）。
MIN_PAYBACK = 1.0
#: 表の列の名前。
LINE, POINTS, HIT_RATE, PAYBACK = "線", "点数", "的中率", "回収率"
#: 複勝の払戻は 100円あたりの円。
_STAKE = 100.0


class BuyLineChooser:
    """「複勝の期待値がこの値以上の穴馬を買う」の線を、検証期間の成績で決める（設計書 16 の 3）。

    決まり: 検証期間で回収率が 100% を超え、買った点が ``MIN_POINTS`` 以上残る線のうち、回収率がいちばん高い線。
    回収率が同じ線が並んだら、点の多い低いほうの線を選ぶ。満たす線が無ければ線なし（NaN）で、その時点・区分には
    「買い」を付けない。テスト期間の結果は使わない。
    例: 線 1.1 で 400点・回収率 1.04、線 1.2 で 180点・回収率 1.08、線 1.3 で 90点・回収率 1.30 なら、
    1.3 は点が足りないので、1.2 を選ぶ。
    """

    def __init__(self, candidates: Sequence[float] = CANDIDATES, min_points: int = MIN_POINTS) -> None:
        self._candidates = tuple(candidates)
        self._min_points = min_points

    def choose(self, value: pd.Series, payout: pd.Series) -> float:
        """検証期間の期待値と払戻（100円あたり。外れは 0 か欠損値）から線を決める。決められなければ NaN。"""
        rates = self.rates(value, payout)
        eligible = rates[(rates[POINTS] >= self._min_points) & (rates[PAYBACK] > MIN_PAYBACK)]
        if eligible.empty:
            return float("nan")
        return float(eligible.loc[eligible[PAYBACK].idxmax(), LINE])

    def rates(self, value: pd.Series, payout: pd.Series) -> pd.DataFrame:
        """線の候補ごとの、買った点数・的中率・回収率（``LINE``・``POINTS``・``HIT_RATE``・``PAYBACK``）。期待値の無い馬は数えない。"""
        values = pd.to_numeric(value, errors="coerce").to_numpy(dtype="float64")
        paid = pd.to_numeric(payout, errors="coerce").fillna(0.0).to_numpy(dtype="float64")
        return pd.DataFrame([self._rate(values, paid, line) for line in self._candidates])

    def _rate(self, values: np.ndarray, paid: np.ndarray, line: float) -> dict[str, float]:
        bought = paid[values >= line]
        points = len(bought)
        return {
            LINE: line, POINTS: points,
            HIT_RATE: float((bought > 0).mean()) if points else float("nan"),
            PAYBACK: float(bought.sum()) / (_STAKE * points) if points else float("nan"),
        }
