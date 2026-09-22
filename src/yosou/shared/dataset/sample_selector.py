"""学習データ・予測用データに入れる行を選ぶクラスに共通の決まり。"""

from __future__ import annotations

from datetime import date
from typing import Protocol

import pandas as pd


class SampleSelector(Protocol):
    """学習データ・予測用データに入れる行の選び方（予想ごとに違う。設計書 06 の図1・08）。

    この決まりを守るクラスを ``DatasetBuilder`` に渡すと、``DatasetBuilder`` は「どの予想か」を知らずに済む。
    """

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        """学習データのサンプルにする行。行の並びと index は ``entries`` のものを引き継ぐ。"""
        ...

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        """1レースのうち、予測する馬の行。予測できないレースなら ``ValueError`` か ``LookupError``。"""
        ...

    def keep_samples(self, rows: pd.DataFrame) -> pd.DataFrame:
        """特徴量を作ったあとに残す行。

        レース内での順位の特徴量は、レースの全出走馬から計算する。一部の馬（人気馬など）だけを
        学習データに入れる予想は、特徴量を作ったあとのここで絞る。全部を残す予想は、そのまま返す。
        """
        ...
