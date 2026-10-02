"""J. 市場の評価（4個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..odds import WIN_RATE
from ..value_types import as_numbers
from .odds_features import WIN_ODDS, OddsFeatures

#: 特徴量の名前。単勝オッズは予測の結果の表にも出すので、外にも見せる。
POPULARITY_RANK = "人気順位"
MARKET_WIN_RATE = WIN_RATE


class MarketFeatures:
    """J. 市場の評価（手本の設計書 09 の J）。``FeatureGroup`` を守る。オッズを使う予想が A〜I に足して使う。

    単勝オッズは「馬券を買う人たち全体が、この馬をどう見ているか」を表す。学習データでは確定オッズ、
    予測では締め切り前のオッズか、利用者が渡したオッズになる（設計書 07）。
    決定木は「同じレースの中で何番目か」「1/オッズの合計」を自分では計算できないので、人気順位と、
    オッズから見た勝率（1/オッズを、レース内で合計が 1 になるようにそろえたもの）も列にしておく。
    オッズから見た3着以内率（Harville の式。既存モデルの修正計画の 2）は、``OddsFeatures`` と同じものを使う。
    オッズが無い馬は、4つとも欠損値になる。
    """

    def __init__(self) -> None:
        self._odds = OddsFeatures()

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        odds = as_numbers(entries["win_odds"])
        rank = odds.groupby(entries["race_id"]).rank(method="min")
        return self._odds.build(records).assign(**{POPULARITY_RANK: rank})
