"""人気薄の1着の予想の区切りごとの予測を、reports/ に pkl で書く・読む。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class LongshotPredictionStore:
    """``<folder>/<作り方>-<時点>.pkl``（予測の表）と ``-log.csv``（学習の記録）。"""

    folder: Path

    def path(self, key: str, timing: str) -> Path:
        return self.folder / f"{key}-{timing}.pkl"

    def exists(self, key: str, timing: str) -> bool:
        return self.path(key, timing).exists()

    def write(self, key: str, timing: str, predictions: pd.DataFrame, log: pd.DataFrame) -> Path:
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.path(key, timing)
        predictions.to_pickle(path)
        log.to_csv(path.with_name(f"{key}-{timing}-log.csv"), index=False, encoding="utf-8-sig")
        return path

    def read(self, key: str, timing: str) -> pd.DataFrame:
        path = self.path(key, timing)
        if not path.exists():
            raise FileNotFoundError(f"予測がありません: {path}（forecast.py train で作る）")
        return pd.read_pickle(path)
