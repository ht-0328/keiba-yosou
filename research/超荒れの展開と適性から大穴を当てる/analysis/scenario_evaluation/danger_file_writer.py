"""新しい予想の 3着以内の確率から、道具「印の成績」の ``--danger`` が読む形の「4着以下になる確率」の予測の表を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

_KEYS = ["レースID", "馬番"]
#: 道具「印の成績」の ``PredictionFile`` が読む列（今の消の予測の表と同じ並び）。
COLUMNS = ("レースID", "開催日", "馬ID", "馬番", "LightGBM", "CatBoost", "確率", "区切り", "期間", "区分")


@dataclass(frozen=True)
class DangerFileWriter:
    """``top3`` は新しい予想の 3着以内の予測の表（検証とテストの行）、``current`` は今の消の予測の表（消にできる人気帯の馬の行）。
    今の消と同じ馬（レースID・馬番）の行だけを残し、確率を 1 − 3着以内の確率にする（LightGBM・CatBoost もそれぞれ）。"""

    top3: pd.DataFrame
    current: pd.DataFrame

    def build(self) -> pd.DataFrame:
        keys = self.current[[*_KEYS, "区切り", "期間"]].astype({"レースID": str}).astype({"馬番": int}).drop_duplicates()
        table = self.top3.astype({"レースID": str}).astype({"馬番": int})
        merged = keys.merge(table.drop(columns=["区分"]), on=[*_KEYS, "区切り", "期間"], how="inner")
        for column in ("LightGBM", "CatBoost", "確率"):
            merged[column] = 1.0 - merged[column]
        merged["区分"] = "全体"
        return merged[list(COLUMNS)].reset_index(drop=True)
