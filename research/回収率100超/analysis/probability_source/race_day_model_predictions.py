"""当日のモデルを区切りごとに学習し直して、その年の3着以内の確率を出す。"""

from __future__ import annotations

import pandas as pd

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, PREDICTION_COLUMN, WalkForwardRunner

from yosou.shared.dataset import HORSE_NO, RACE_DATE, RACE_ID, TrainingData

#: 新しい確率の列の名前（2つのモデルの平均。レース内でそろえ直す前）。
MODEL_PROBABILITY = "当日のモデルの3着以内の確率"


class RaceDayModelPredictions:
    """予想「近走と適性から3着以内を予想」の当日のモデル（今の材料 ＋ 券種の支持 N）を、区切りごとに学習し直して予測する。

    作り方（``variant``）は研究「一番人気を疑う」の移したあとの確かめの ``pool-race_day`` と同じもので、本番の保存済みモデルは
    使わない（本番のモデルは別の作業が学習し直すことがあり、その年より後のデータで学んでいる）。学習と予測は
    ``WalkForwardRunner``（LightGBM と CatBoost を予想の初期値で学び、確率を平均する）に任せ、ここではテストの年の行だけを
    元の予測と突き合わせられる形（``rid``・``horse_no``・``year``）にする。
    """

    def __init__(self, runner: WalkForwardRunner, variant: ModelVariant) -> None:
        self._runner = runner
        self._variant = variant

    def run(self, data: TrainingData) -> tuple[pd.DataFrame, pd.DataFrame]:
        """（テストの年の予測, 学習の記録）。予測の列は rid・horse_no・year・``MODEL_PROBABILITY``。"""
        predictions, log = self._runner.run(data, self._variant)
        tested = predictions[predictions[PART] == PART_TEST]
        tested = tested[tested[HORSE_NO].notna()]
        frame = pd.DataFrame({
            "rid": tested[RACE_ID].astype(str).to_numpy(),
            "horse_no": tested[HORSE_NO].astype(int).to_numpy(),
            "year": pd.to_datetime(tested[RACE_DATE]).dt.year.to_numpy(),
            MODEL_PROBABILITY: tested[PREDICTION_COLUMN].astype(float).to_numpy(),
        })
        return frame, log
