"""J. 市場の評価（3個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..value_types import as_numbers

#: 特徴量の名前。単勝オッズは予測の結果の表にも出すので、外にも見せる。
WIN_ODDS = "単勝オッズ"
POPULARITY_RANK = "人気順位"
MARKET_WIN_RATE = "オッズから見た勝率"


class MarketFeatures:
    """J. 市場の評価（手本の設計書 09 の J）。``FeatureGroup`` を守る。オッズを使う予想が A〜I に足して使う。

    単勝オッズは「馬券を買う人たち全体が、この馬をどう見ているか」を表す。学習データでは確定オッズ、
    予測では締め切り前のオッズか、利用者が渡したオッズになる（設計書 07）。
    決定木は「同じレースの中で何番目か」「1/オッズの合計」を自分では計算できないので、人気順位と、
    オッズから見た勝率（1/オッズを、レース内で合計が 1 になるようにそろえたもの）も列にしておく。
    オッズが無い馬は、3つとも欠損値になる。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        race = entries["race_id"]
        odds = as_numbers(entries["win_odds"])
        inverse = 1.0 / odds
        return pd.DataFrame({
            WIN_ODDS: odds,
            POPULARITY_RANK: odds.groupby(race).rank(method="min"),
            MARKET_WIN_RATE: inverse / inverse.groupby(race).transform("sum"),
        }, index=entries.index)
