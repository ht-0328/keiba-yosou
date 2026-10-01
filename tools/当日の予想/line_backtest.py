"""保存したモデルで、1つの期間の馬を期待値の線ごとに複勝で買った結果を出す。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from yosou.custom_binary import workflow
from yosou.custom_binary.evaluation import bet_result, expected_values
from yosou.shared.dataset import TrainingData


class LineBacktest:
    """当日の予想と同じ計算（3着以内の確率 × 複勝の想定払戻倍率）で期待値を出し、線ごとに1点100円で買った結果を返す。

    オッズは確定オッズなので、買う時点のオッズで買ったときの結果とは違いうる（``evaluation.PAYBACK_NOTE``）。
    """

    def __init__(self, model: workflow.LoadedModel) -> None:
        self._model = model

    def results(self, data: TrainingData, lines: Sequence[float]) -> dict[float, dict]:
        """線ごとの結果（``bet_result`` の辞書。点数・複勝回収率・複勝回収率の下限 …）。"""
        probability = self._model.ensemble.predict_proba(data) if len(data) else np.array([])
        value = expected_values(data, probability, self._model.settings.target, self._model.place_price)
        value = np.nan_to_num(value, nan=-1.0)
        return {line: bet_result(data, value >= line, f"期待値{line:g}以上") for line in lines}
