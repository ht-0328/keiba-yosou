"""予測用データと、それを予測するモデルの組（予測の流れの途中の値）。"""

from __future__ import annotations

from dataclasses import dataclass

from ..dataset import PredictionData
from .segmented_prediction import SegmentedPrediction


@dataclass(frozen=True)
class PreparedPrediction:
    """予測用データと、それを予測するモデル（3着以内と1着）。当日に券種のオッズが無ければ、N を使わないモデル。

    ``top3_data`` は3着以内のモデルに渡す（Q を外し、``extras`` の列（展開スコア S）を足したもの）。``win_data`` は1着のモデルに渡す
    （Q を含み、目的変数と基準を1着に持ち替え、``win_extras`` の列を足したもの）。``data`` はその元（ID 列と材料）。
    """

    data: PredictionData
    top3_data: PredictionData
    win_data: PredictionData
    predictor: SegmentedPrediction
    win_predictor: SegmentedPrediction | None
