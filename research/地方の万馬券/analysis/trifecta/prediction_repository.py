"""全頭の予想の予測の表（backtest が書いた pkl）を読み、馬ごとの 3着以内の確率と 1着の確率にする。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

#: 予測の表の列（道具「印の成績」と同じ）。
_RACE, _HORSE_NO, _PROBABILITY = "レースID", "馬番", "確率"
P3, P1 = "p3", "p1"


@dataclass(frozen=True)
class PredictionRepository:
    """``top3_pkl``（3着以内）と ``win_pkl``（1着）を馬番で突き合わせ、``race_id``・``horse_no``・``p3``・``p1`` にする。"""

    top3_pkl: Path
    win_pkl: Path

    def load(self) -> pd.DataFrame:
        top3 = self._read(self.top3_pkl, P3)
        win = self._read(self.win_pkl, P1)
        return top3.merge(win, on=["race_id", "horse_no"], how="inner")

    def _read(self, path: Path, name: str) -> pd.DataFrame:
        table = pd.read_pickle(path)
        return pd.DataFrame({"race_id": table[_RACE].astype(str), "horse_no": table[_HORSE_NO].astype(int), name: table[_PROBABILITY].astype(float)})
