"""確率を直すモデルを年ごとに学び直し（その年より前の年だけで学ぶ）、その年の確率を直す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.win_correction import WinCorrectionFeatures, WinCorrectionModel

#: 学ぶのに使う最低の年数（2020年からの予測なので、2022年から確かめる）。1年だけで学んだモデルは期待値を出しすぎた（docs/02）。
MIN_TRAINING_YEARS = 2


@dataclass(frozen=True)
class WalkForwardModel:
    """``final`` は学習の表（``TrainingTable.build``。列 ``year``・``won`` を含む）。``predict`` は、``final`` と同じ形の表（確定オッズか締め切り前の断面）
    の各年の行に、その年より前の ``final`` だけで学んだモデルの直した確率（列 ``corrected``）を付けて返す。最初の ``MIN_TRAINING_YEARS`` 年は付けない。"""

    final: pd.DataFrame

    def predict(self, tables: list[pd.DataFrame]) -> list[pd.DataFrame]:
        features = WinCorrectionFeatures()
        first = int(self.final["year"].min()) + MIN_TRAINING_YEARS
        years = range(first, int(self.final["year"].max()) + 1)
        outputs = [table.assign(corrected=float("nan")) for table in tables]
        train_frame = features.frame(self.final)
        for year in years:
            learned = self.final["year"] < year
            model = WinCorrectionModel.fit(train_frame[learned], self.final.loc[learned, "won"])
            for output in outputs:
                rows = output["year"] == year
                if rows.any():
                    output.loc[rows, "corrected"] = model.probabilities(features.frame(output[rows]), output.loc[rows, "race_id"]).to_numpy()
        return [output[output["corrected"].notna()].reset_index(drop=True) for output in outputs]
