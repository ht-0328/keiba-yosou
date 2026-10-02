"""K. 単勝オッズから見た評価（3個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..odds import TOP3_RATE, WIN_RATE, MarketPlaces
from ..value_types import as_numbers

#: 特徴量の名前。単勝オッズは予測の結果の表にも出すので、外にも見せる。
WIN_ODDS = "単勝オッズ"


class OddsFeatures:
    """K. 単勝オッズから見た評価（既存モデルの修正計画の 2「オッズの使い方」）。``FeatureGroup`` を守る。

    単勝オッズそのものと、そこから出したオッズから見た勝率・3着以内率。人気順位だけでは分からない
    「支持の強さ」（同じ10番人気でも 30倍か 200倍か）を、決定木が使えるようにする。
    人気を使う予想（人気馬・穴馬）が、人気の履歴（J）に足して使う。オッズが無い馬（木曜）は欠損値。
    """

    def __init__(self) -> None:
        self._places = MarketPlaces()

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        places = self._places.of(entries)
        return pd.DataFrame({
            WIN_ODDS: as_numbers(entries["win_odds"]),
            WIN_RATE: places[WIN_RATE],
            TOP3_RATE: places[TOP3_RATE],
        }, index=entries.index)
