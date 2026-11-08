"""今のモデルと同じ作りの、区切りごとの当日の1着の予測（テスト期間の行）を読み、レースの中で合計 1 にそろえる。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from 印の成績.prediction_file import TEST, PredictionFile

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
#: 既定の予測（研究「複勝以外の回収率100超」が作った、2019年からの区切りごとの当日の1着の予測。その半年より前だけで学び直したもの）。
DEFAULT_PREDICTIONS = (_PROJECT_ROOT / "reports" / "複勝以外の回収率100超" / "predictions-2019から"
                       / "dscore_finish_race_day" / "win-race_day.pkl")


@dataclass(frozen=True)
class FoldWinPredictions:
    """1行 = 1頭。列は race_id・horse_no・model（レースの中でそろえた1着の確率）。"""

    path: Path = DEFAULT_PREDICTIONS

    def load(self) -> pd.DataFrame:
        table = PredictionFile(str(self.path)).load()
        tested = table.loc[table["period"] == TEST, ["race_id", "horse_no", "probability"]].copy()
        tested["horse_no"] = tested["horse_no"].astype(float)
        tested["model"] = tested["probability"] / tested.groupby("race_id")["probability"].transform("sum")
        return tested[["race_id", "horse_no", "model"]]
