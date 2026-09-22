"""学習データ・予測用データに入れる行を選ぶ。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.dataset import JUMP, FlatRunnerFilter


class RunnerSelector:
    """入れる行を選ぶ（設計書 06 の図1）。``SampleSelector`` を守る。

    3つの問い「障害レースか」「出走したか」「学習データの始まり以降か」のうち、はじめの2つは学習と予測に共通で、
    共通の ``FlatRunnerFilter`` が答える。3つ目は学習だけ（これから走るレースは、常に学習データの始まり以降）。
    """

    def __init__(self) -> None:
        self._flat_runners = FlatRunnerFilter()

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        """学習データのサンプルにする行。``train_first_day`` より前（ウォームアップ期間）の行は、
        過去走の計算にだけ使うので入れない（設計書 08 の 3）。
        """
        runners = self._flat_runners.apply(entries)
        return runners[runners["race_date"] >= pd.Timestamp(train_first_day)]

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        """予測する馬の行。障害レースなら ``ValueError``、出走する馬がいなければ ``LookupError``。"""
        if (entries["surface"] == JUMP).any():
            raise ValueError(f"障害レースは予測しません（学習データに入れていないため）: {race_id}")
        runners = self._flat_runners.apply(entries)
        if runners.empty:
            raise LookupError(f"出走する馬がいません（全頭が取消・除外）: {race_id}")
        return runners

    def keep_samples(self, rows: pd.DataFrame) -> pd.DataFrame:
        """特徴量を作ったあとに残す行。この予想は出走した全頭を入れるので、そのまま返す（設計書 08 の 3）。"""
        return rows
