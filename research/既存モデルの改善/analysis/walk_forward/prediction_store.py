"""予測の表と学習の記録を、ファイルに書く・読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: 予測の表と学習の記録のファイル名の後ろ。
_PREDICTIONS_SUFFIX = ".pkl"
_LOG_SUFFIX = "-log.csv"


class PredictionStore:
    """予想 × 作り方 ごとの予測の表を ``<root>/<予想の名前>/<作り方>.pkl`` に、学習の記録を ``<作り方>-log.csv`` に書く。"""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def write(self, model: str, key: str, predictions: pd.DataFrame, log: pd.DataFrame) -> Path:
        folder = self._root / model
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{key}{_PREDICTIONS_SUFFIX}"
        predictions.to_pickle(path)
        log.to_csv(folder / f"{key}{_LOG_SUFFIX}", index=False, encoding="utf-8-sig")
        return path

    def read(self, model: str, key: str) -> pd.DataFrame:
        """予測の表。無ければ ``FileNotFoundError``。"""
        return pd.read_pickle(self._root / model / f"{key}{_PREDICTIONS_SUFFIX}")

    def exists(self, model: str, key: str) -> bool:
        return (self._root / model / f"{key}{_PREDICTIONS_SUFFIX}").exists()
