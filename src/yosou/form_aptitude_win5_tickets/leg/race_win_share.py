"""1レースの全頭の1着の確率を、合計が 1 になるようにそろえる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_ID
from yosou.shared.feature.group import WIN_ODDS
from yosou.shared.feature.odds import MarketWinProbability
from yosou.shared.workflow import WIN_PROBABILITY

from .leg_columns import EDGE, MARKET, SHARE


class RaceWinShare:
    """1レースの予測の結果（``LegWinPredictor``）に、そろえた1着の確率・オッズから見た勝率・上乗せの列を足す（設計書 10 の 1.）。

    今のモデルは1頭ずつ確率を出す（二値分類）ので、同じレースの全頭を足しても 1 にならない。WIN5 の組の確率は5レースの確率の
    かけ算なので、2つのモデルを平均したあとに、レースの中で割り算でそろえる。1着の確率か単勝オッズの無い馬（取消など）は除く。
    """

    def __init__(self) -> None:
        self._market = MarketWinProbability()

    def of(self, prediction: pd.DataFrame) -> pd.DataFrame:
        """``prediction`` に ``SHARE``・``MARKET``・``EDGE`` を足した表（1着の確率か単勝オッズの無い馬を除く）。"""
        probability = pd.to_numeric(prediction[WIN_PROBABILITY], errors="coerce")
        odds = pd.to_numeric(prediction[WIN_ODDS], errors="coerce")
        usable = prediction.loc[(probability > 0) & (odds > 0)].reset_index(drop=True)
        if usable.empty:
            raise LookupError("1着の確率と単勝オッズのそろった馬が1頭もいません")
        share = usable[WIN_PROBABILITY] / usable[WIN_PROBABILITY].sum()
        market = self._market.of(usable[RACE_ID], usable[WIN_ODDS])
        return usable.assign(**{SHARE: share, MARKET: market, EDGE: share / market})
