"""学習データ・予測用データに入れる行を選ぶ。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.dataset import JUMP, FlatRunnerFilter

from 共通.stakes import GRADE_NAMES

#: 対象のグレードコード（G1・G2・G3）。
GRADED: tuple[str, ...] = tuple(GRADE_NAMES)


class RunnerSelector:
    """入れる行を選ぶ（設計書 06 の図1）。``SampleSelector`` を守る。

    手本（近走と適性）との違いは1つ: **重賞（グレードコード A・B・C）の行だけ**を入れる。
    障害レースと出走しなかった馬を除くのは、共通の ``FlatRunnerFilter``。
    """

    def __init__(self) -> None:
        self._flat_runners = FlatRunnerFilter()

    def training_samples(self, entries: pd.DataFrame, train_first_day: date) -> pd.DataFrame:
        """学習データのサンプルにする行。重賞だけ。``train_first_day`` より前（ウォームアップ期間）は入れない。"""
        runners = self._flat_runners.apply(entries)
        graded = runners[runners["grade_code"].isin(GRADED)]
        return graded[graded["race_date"] >= pd.Timestamp(train_first_day)]

    def prediction_runners(self, entries: pd.DataFrame, race_id: str) -> pd.DataFrame:
        """予測する馬の行。重賞でないレース・障害レースなら ``ValueError``、出走する馬がいなければ ``LookupError``。"""
        if (entries["surface"] == JUMP).any():
            raise ValueError(f"障害レースは予測しません（学習データに入れていないため）: {race_id}")
        if not entries["grade_code"].isin(GRADED).any():
            raise ValueError(f"重賞（G1・G2・G3）ではないので予測しません（この予想は重賞だけで学習しているため）: {race_id}")
        runners = self._flat_runners.apply(entries)
        if runners.empty:
            raise LookupError(f"出走する馬がいません（全頭が取消・除外）: {race_id}")
        return runners

    def keep_samples(self, rows: pd.DataFrame) -> pd.DataFrame:
        """特徴量を作ったあとに残す行。この予想は重賞の出走した全頭を入れるので、そのまま返す。"""
        return rows
