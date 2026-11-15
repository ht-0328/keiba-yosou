"""印を付けた1レースの表から、「裏まで買うか」を決めるモデルの材料（1レース1行）を作る。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from 今週の予想.forecast_columns import (
    MARK,
    MARKET_TOP3,
    MARKET_WIN,
    PLACE_VALUE,
    POPULARITY,
    PROBABILITY,
    WIN_ODDS,
    WIN_PROBABILITY,
    WIN_VALUE,
)
from 今週の予想.harville_reverse import HarvilleReverse
from 今週の予想.mark_rule import TOP_MARK, VALUE_MARK
from 今週の予想.ticket_rules import PLACE_VALUE_LINE

#: 裏の相手の印（☆ は複勝の期待値が ``PLACE_VALUE_LINE`` 以上のときだけ。買い目の相手と同じ）。
PARTNER_MARKS: tuple[str, ...] = ("○", "▲")
#: モデルの材料の並び（学習と予測で同じ並びにする）。
FEATURES: tuple[str, ...] = (
    "裏_モデル", "裏_市場", "◎1着率", "◎3着内率", "◎市場1着率", "◎市場3着内率", "◎人気", "◎単勝", "◎複勝の期待値", "◎単勝の期待値",
    "相手の最大1着率", "相手の最大市場1着率", "相手の最大3着内率", "相手の1着率の合計", "相手の市場1着率の合計", "相手の数", "頭数",
    "◎の1着率÷3着内率", "相手÷◎（1着率）",
)
#: 確率の無い馬を 0 にしたとき、合計 1 にそろえられるように足す小さな数。
_TINY = 1e-6


class ReverseExactaFeatures:
    """印を付けた1レースの表（1行 = 1頭。``MarkRule.assign`` の戻り値）から、``FEATURES`` の材料を作る。

    裏は「1着が相手（○▲☆）のどれかで、◎ が2着か3着」。材料は ◎ と相手の確率・市場の見立て・期待値と、今の予想の1着の確率と
    市場の1着の確率（単勝オッズから）のそれぞれから Harville で出した裏の当たる確率（``HarvilleReverse``）。
    ◎ がちょうど1頭でないか、相手がいなければ None（裏を買えない）。頭数は列 ``field_size`` があればその値、無ければ行の数。
    """

    def __init__(self) -> None:
        self._harville = HarvilleReverse()

    def of(self, race: pd.DataFrame) -> dict[str, Any] | None:
        race = race.reset_index(drop=True)
        tops = race.index[race[MARK] == TOP_MARK]
        partners = self.partners(race)
        if len(tops) != 1 or not partners:
            return None
        top = race.loc[tops[0]]
        mates = race.loc[partners]
        win_model = race[WIN_PROBABILITY].fillna(0).to_numpy(dtype=float) + _TINY
        win_market = race[MARKET_WIN].fillna(0).to_numpy(dtype=float) + _TINY
        field = race["field_size"].iloc[0] if "field_size" in race.columns else len(race)
        return {
            "裏_モデル": self._harville.of(win_model, int(tops[0]), partners),
            "裏_市場": self._harville.of(win_market, int(tops[0]), partners),
            "◎1着率": top[WIN_PROBABILITY], "◎3着内率": top[PROBABILITY], "◎市場1着率": top[MARKET_WIN], "◎市場3着内率": top[MARKET_TOP3],
            "◎人気": top[POPULARITY], "◎単勝": top[WIN_ODDS], "◎複勝の期待値": top[PLACE_VALUE], "◎単勝の期待値": top[WIN_VALUE],
            "相手の最大1着率": mates[WIN_PROBABILITY].max(), "相手の最大市場1着率": mates[MARKET_WIN].max(),
            "相手の最大3着内率": mates[PROBABILITY].max(), "相手の1着率の合計": mates[WIN_PROBABILITY].sum(),
            "相手の市場1着率の合計": mates[MARKET_WIN].sum(), "相手の数": len(partners), "頭数": field,
            "◎の1着率÷3着内率": _ratio(top[WIN_PROBABILITY], top[PROBABILITY]),
            "相手÷◎（1着率）": _ratio(mates[WIN_PROBABILITY].max(), top[WIN_PROBABILITY]),
        }

    @staticmethod
    def partners(race: pd.DataFrame) -> list[int]:
        """相手（○▲ と、複勝の期待値が ``PLACE_VALUE_LINE`` 以上の ☆）の行の位置。``race`` は index を 0 から振り直した表。"""
        partner = race[MARK].isin(PARTNER_MARKS) | ((race[MARK] == VALUE_MARK) & (race[PLACE_VALUE] >= PLACE_VALUE_LINE))
        return [int(at) for at in race.index[partner]]

    def frame(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        """材料の辞書の並びを、``FEATURES`` の並びの表（数の列）にする。"""
        return pd.DataFrame(rows, columns=list(FEATURES)).astype(float)


def _ratio(numerator: Any, denominator: Any) -> float:
    """割り算。分母が 0 か欠損値なら欠損値。"""
    if denominator is None or pd.isna(denominator) or denominator == 0:
        return np.nan
    return float(numerator) / float(denominator)
