"""学習データ・予測用データに入れる行を選ぶ。"""

from __future__ import annotations

from datetime import date

import pandas as pd

#: 学習データに入れる最初の開催日。これより前はウォームアップ期間（設計書 08 の 3）。
SAMPLE_FIRST_DAY = date(2024, 1, 1)
#: 障害レースの芝ダ。学習データに入れない。
_JUMP = "障害"


class RunnerSelector:
    """入れる行を選ぶ（設計書 06 の図1）。

    3つの問い「障害レースか」「出走したか」「2024年1月以降か」のうち、はじめの2つは学習と予測に共通。
    3つ目は学習だけ（これから走るレースは、常に 2024年1月以降）。
    """

    def training_samples(self, entries: pd.DataFrame) -> pd.DataFrame:
        """学習データのサンプルにする行。ウォームアップ期間の行は、過去走の計算にだけ使うので入れない。"""
        runners = self._flat_runners(entries)
        return runners[runners["race_date"] >= pd.Timestamp(SAMPLE_FIRST_DAY)]

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        """予測する馬の行。障害レースなら ``ValueError``、出走する馬がいなければ ``LookupError``。"""
        if (entries["surface"] == _JUMP).any():
            raise ValueError(f"障害レースは予測しません（学習データに入れていないため）: {race_id}")
        runners = self._flat_runners(entries)
        if runners.empty:
            raise LookupError(f"出走する馬がいません（全頭が取消・除外）: {race_id}")
        return runners

    def _flat_runners(self, entries: pd.DataFrame) -> pd.DataFrame:
        """障害レースと、出走しなかった馬（出走取消・発走除外・競走除外）を除いた行。"""
        is_flat = entries["surface"] != _JUMP
        has_run = entries["ran"].eq(True)
        return entries[is_flat & has_run]
