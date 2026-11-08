"""騎手と調教師の、前の年の勝率を足す（今回の騎手・前の走の騎手・調教師）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PeopleRates:
    """出走の表に ``jockey_rate``（今回の騎手の前の年の勝率）・``prev_jockey_rate``（前の走の騎手の前の年の勝率）・
    ``trainer_rate``（調教師の前の年の勝率）を足す。前の年の値なので、レースの前に分かる。前の年に乗っていなければ欠損値。
    ``prev_jockey`` の列（``RunnerHistory`` が足す）が要る。"""

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        jockey = self._yearly(runners, "jockey_code")
        trainer = self._yearly(runners, "trainer_code")
        frame = runners.merge(jockey.rename(columns={"rate": "jockey_rate"}), on=["jockey_code", "year"], how="left")
        previous = jockey.rename(columns={"jockey_code": "prev_jockey", "rate": "prev_jockey_rate"})
        frame = frame.merge(previous, on=["prev_jockey", "year"], how="left")
        return frame.merge(trainer.rename(columns={"rate": "trainer_rate"}), on=["trainer_code", "year"], how="left")

    @staticmethod
    def _yearly(runners: pd.DataFrame, key: str) -> pd.DataFrame:
        """人ごと・年ごとの勝率を、次の年の行として返す（列は key・year・rate）。"""
        wins = (runners["finish"] == 1).astype(float)
        rates = wins.groupby([runners[key], runners["year"]]).mean().rename("rate").reset_index()
        rates["year"] = rates["year"] + 1
        return rates
