"""印の組の表の置き場所（pkl。作るのに時間がかかるので、買い方を試すたびに作り直さない）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_NAME = "印の組"


class MarkTableStore:
    """``suffix`` は当てはめ方の違う表の名前の後ろに付ける言葉（例 ``-前の年``。入れ替えは空）。"""

    def __init__(self, folder: Path, suffix: str = "") -> None:
        self._folder = folder
        self._suffix = suffix

    @property
    def path(self) -> Path:
        return self._folder / f"{_NAME}{self._suffix}.pkl"

    def save(self, table: pd.DataFrame) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        table.to_pickle(self.path)

    def load(self) -> pd.DataFrame:
        if not self.path.is_file():
            raise FileNotFoundError(f"印の組の表がありません。先に --build で作ってください: {self.path}")
        return pd.read_pickle(self.path)
