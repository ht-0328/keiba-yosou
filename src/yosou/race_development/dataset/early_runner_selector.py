"""学習データ・予測用データに入れる行（出走馬）を選ぶ。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.dataset import JUMP, FlatRunnerFilter


class EarlyRunnerSelector:
    """入れる行を選ぶ（設計書 06 の図3）。``SampleSelector`` を守る。

    平地・出走した馬・学習データの始まり以降の全頭を残す。全頭を残すのは、同じレースの馬との比較（L・O）と、
    レース単位の集約（P・U）を、レースの全出走馬から作るためである。正解の付かない行（直線コースなど）も落とさず、
    目的変数を欠損値にして、予想ごとに ``with_label()`` で外す。
    """

    def __init__(self) -> None:
        self._flat_runners = FlatRunnerFilter()

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        """学習データのレースの出走馬の行。``train_first_day`` より前（ウォームアップ期間）は入れない。"""
        runners = self._flat_runners.apply(entries)
        return runners[runners["race_date"] >= pd.Timestamp(train_first_day)]

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        """予測するレースの出走馬の行。障害レースなら ``ValueError``、出走する馬がいなければ ``LookupError``。"""
        if (entries["surface"] == JUMP).any():
            raise ValueError(f"障害レースは予測しません（学習データに入れていないため）: {race_id}")
        runners = self._flat_runners.apply(entries)
        if runners.empty:
            raise LookupError(f"出走する馬がいません（全頭が取消・除外）: {race_id}")
        return runners

    def keep_samples(self, rows: pd.DataFrame) -> pd.DataFrame:
        """全頭を残すので、そのまま返す。"""
        return rows
