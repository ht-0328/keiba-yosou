"""全頭の予想の予測の表（backtest が書いた pkl）から、馬ごとの 3着以内・1着の確率を、平均と LightGBM・CatBoost のそれぞれで読む。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

#: 予測の表の列（道具「印の成績」と同じ）。
_RACE, _HORSE_NO, _PROBABILITY, _LGB, _CAT = "レースID", "馬番", "確率", "LightGBM", "CatBoost"
TOP3_FILE, WIN_FILE = "race_day.pkl", "race_day-1着.pkl"


@dataclass(frozen=True)
class MemberPredictions:
    """``folder`` の当日の予測を読み、``race_id``（文字列）・``horse_no``・``p3``・``p3_lgb``・``p3_cat``・``p1``・``p1_lgb``・``p1_cat`` にする。"""

    folder: Path

    def load(self) -> pd.DataFrame:
        top3 = self._read(self.folder / TOP3_FILE, "p3")
        win = self._read(self.folder / WIN_FILE, "p1")
        table = top3.merge(win, on=["race_id", "horse_no"], how="inner")
        return table.drop_duplicates(["race_id", "horse_no"], keep="last").reset_index(drop=True)

    def _read(self, path: Path, name: str) -> pd.DataFrame:
        table = pd.read_pickle(path)
        return pd.DataFrame({
            "race_id": table[_RACE].astype(str), "horse_no": pd.to_numeric(table[_HORSE_NO], errors="coerce").astype(int),
            name: pd.to_numeric(table[_PROBABILITY], errors="coerce").astype(float),
            f"{name}_lgb": pd.to_numeric(table[_LGB], errors="coerce").astype(float), f"{name}_cat": pd.to_numeric(table[_CAT], errors="coerce").astype(float),
        })
