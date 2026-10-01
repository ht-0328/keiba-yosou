"""「荒れるレースだけ買う」使い方の線引きを決めるための、しきい値ごとの数え上げ。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import EnsembleModel

from ..dataset.upset_level import UpsetLevel

#: 並べる「中荒れ以上の確率」のしきい値。0 は全レース（しきい値を使わないとき）。
THRESHOLDS: tuple[float, ...] = (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
#: 結果の列の名前。
THRESHOLD = "しきい値"
RACES = "レース数"
UPSET_SHARE = "実際に中荒れ以上だった割合"
UPSET_COVERAGE = "中荒れ以上のうち選んだ割合"
COLUMNS: tuple[str, ...] = (THRESHOLD, RACES, UPSET_SHARE, UPSET_COVERAGE)


class UpsetThresholdSummary:
    """モデルの「中荒れ以上の確率」がしきい値以上のレースを「荒れる」とみなしたときの、レース数と、そのうち実際に
    中荒れ以上だった割合を、しきい値ごとに数える（設計書 16 の 3「荒れるレースだけ買う使い方の線引き」）。

    しきい値そのものは決めない。検証データでこの表を並べ、利用者が線を選ぶための材料にする。
    """

    def summarize(self, ensemble: EnsembleModel, data: TrainingData) -> pd.DataFrame:
        """``data`` は、その時点で使う列だけにした学習に使っていないデータ。1行 = 1つのしきい値。"""
        probabilities = ensemble.predict_proba(data)
        upset_probability = probabilities[:, UpsetLevel.MID.value:].sum(axis=1)
        is_upset = data.label.to_numpy() >= UpsetLevel.MID.value
        return pd.DataFrame(
            [self._row(threshold, upset_probability >= threshold, is_upset) for threshold in THRESHOLDS],
            columns=list(COLUMNS),
        )

    def _row(self, threshold: float, chosen: np.ndarray, is_upset: np.ndarray) -> list[object]:
        return [threshold, int(chosen.sum()), self._share(is_upset[chosen]), self._share(chosen[is_upset])]

    def _share(self, flags: np.ndarray) -> float:
        """真の割合。要素が無ければ NaN。"""
        if len(flags) == 0:
            return float("nan")
        return float(flags.mean())
