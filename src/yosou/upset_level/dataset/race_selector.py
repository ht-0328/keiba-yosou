"""学習データ・予測用データに入れる行（出走馬）を選ぶ。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.dataset import JUMP, FlatRunnerFilter


class RaceSelector:
    """入れる行を選ぶ（設計書 06 の図1 の、はじめの3つの問い）。``SampleSelector`` を守る。

    1行 = 1レースの学習データでも、まず出走馬の行（1頭ごと）を選ぶ。平地・出走した馬・学習データの始まり以降の
    全頭を残し、行は減らさない（レース単位の集約は、そのあとの ``RaceFeatureBuilder`` が行う）。
    """

    def __init__(self) -> None:
        self._flat_runners = FlatRunnerFilter()

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        """学習データのレースの出走馬の行。``train_first_day`` より前（ウォームアップ期間）の行は、
        近走と過去の荒れ率の計算にだけ使うので入れない（設計書 08 の 3）。
        """
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
        """特徴量を作ったあとに残す行。全頭を残すので、そのまま返す。"""
        return rows
