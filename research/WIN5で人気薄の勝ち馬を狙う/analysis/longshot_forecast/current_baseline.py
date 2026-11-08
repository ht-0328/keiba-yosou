"""出発点にする、今のモデルのそろえた1着の確率のロジット（区切りごとの予測のテスト期間の値。どれもその半年より前で学んだもの）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from yosou.shared.feature import PredictionTiming

from 印の成績.prediction_file import TEST, PredictionFile
from 印の成績.win5_prediction_files import DEFAULT_DAY_BEFORE, DEFAULT_RACE_DAY

from .longshot_data import HORSE_NO, RACE_ID

#: 時点 → 今のモデルの区切りごとの1着の予測（道具「印の成績」の ``--win5`` の既定と同じ。当日は 2015年から、前日は 2019年から）。
CURRENT_FILES: dict[PredictionTiming, Path] = {PredictionTiming.RACE_DAY: DEFAULT_RACE_DAY, PredictionTiming.DAY_BEFORE: DEFAULT_DAY_BEFORE}
_EDGE = 1e-4
#: 返す列の名前。
LOGIT = "今のモデルのロジット"


@dataclass(frozen=True)
class CurrentBaseline:
    """1行 = 1頭。列は レースID・馬番・``LOGIT``（レースの中で合計 1 にそろえた確率のロジット）。"""

    def of(self, timing: PredictionTiming) -> pd.DataFrame:
        table = PredictionFile(str(CURRENT_FILES[timing])).load()
        tested = table.loc[table["period"] == TEST, ["race_id", "horse_no", "probability"]]
        share = tested["probability"] / tested.groupby("race_id")["probability"].transform("sum")
        clipped = share.clip(_EDGE, 1 - _EDGE)
        return pd.DataFrame({RACE_ID: tested["race_id"].astype(str), HORSE_NO: tested["horse_no"].astype(int),
                             LOGIT: np.log(clipped / (1 - clipped))})
