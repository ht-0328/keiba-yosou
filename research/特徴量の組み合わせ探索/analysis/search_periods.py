"""探索の期間の区切り。見つける期間・確かめる期間・最後に1回だけ見る期間を分ける。"""

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class SearchPeriods:
    """``discover`` で候補を見つけ（モデルなら学習）、``confirm`` で確かめ（モデルなら早期終了と買い方の選択）、
    ``test`` は採否を決めたあとに1回だけ見る。どの期間も、前の期間の結果を見て決めたことを後ろで確かめる順。
    """

    warmup_from: date = date(2016, 1, 1)
    discover_from: date = date(2017, 1, 1)
    confirm_from: date = date(2023, 1, 1)
    test_from: date = date(2025, 1, 1)

    def names(self, days: pd.Series) -> pd.Series:
        """開催日ごとの期間の名前（見つける・確かめる・テスト）。"""
        return pd.Series(
            pd.cut(
                days, [pd.Timestamp(self.discover_from), pd.Timestamp(self.confirm_from), pd.Timestamp(self.test_from),
                       pd.Timestamp.max], right=False, labels=["見つける", "確かめる", "テスト"],
            ), index=days.index,
        )

    def training(self) -> dict:
        """custom_binary の YAML の training と同じ形。"""
        return {
            "warmup_from": self.warmup_from, "train_from": self.discover_from,
            "valid_from": self.confirm_from, "test_from": self.test_from,
        }
