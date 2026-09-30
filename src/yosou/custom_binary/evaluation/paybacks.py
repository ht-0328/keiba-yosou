"""その確率で買った場合の回収率（買い方ごと）。"""

import numpy as np
import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import RACE_ID
from yosou.shared.place_value import PlacePriceEstimator

from .bet_result import BetResult
from .expected_value import ExpectedValue
from .payback_rules import EXPECTED_VALUE_LINES


class Paybacks:
    """対象の全頭・各レースの確率1位・期待値の下限ごとに買った回収率。馬券外は確率が低いほど「来る」側として扱う。"""

    def of(self, data: TrainingData, probability: np.ndarray, target: str,
           place_price: PlacePriceEstimator | None = None) -> list[dict]:
        bet = BetResult()
        if len(data) == 0:
            return [bet.of(data, np.zeros(0, dtype=bool), "対象の全頭")]
        coming = 1 - probability if target == "馬券外" else probability
        results = [
            bet.of(data, np.ones(len(data), dtype=bool), "対象の全頭（モデルなし）"),
            bet.of(data, self._top_pick_rows(data, coming), "各レースで確率1位"),
        ]
        value = ExpectedValue().of(data, probability, target, place_price)
        for line in EXPECTED_VALUE_LINES:
            results.append(bet.of(data, np.nan_to_num(value, nan=-1.0) >= line, f"期待値{line:g}以上"))
        return results

    def _top_pick_rows(self, data: TrainingData, score: np.ndarray) -> np.ndarray:
        """各レースで ``score`` がいちばん高い馬（対象の馬の中で）。"""
        frame = pd.DataFrame({"race": data.ids[RACE_ID].to_numpy(), "score": score})
        rows = np.zeros(len(frame), dtype=bool)
        rows[frame.groupby("race", sort=False)["score"].idxmax().to_numpy()] = True
        return rows
