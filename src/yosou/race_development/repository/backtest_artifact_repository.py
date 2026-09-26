"""年ごとの確かめの、途中の結果と表を読み書きする。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class BacktestArtifactRepository:
    """年ごとの予測・精算の表を ``<root>/<年>/<名前>.pkl`` に、結果の表（Markdown）を ``<root>/<名前>.md`` に書く（設計書 04 の「repository/」）。

    止まったら、終わった年の表を読んで続きから再開する。払戻などの JV-Data 由来の数値を含むので、``root`` は
    Git の対象外（``reports/race_development/backtest/``）にする。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def exists(self, year: int, name: str) -> bool:
        return self._table_path(year, name).exists()

    def load(self, year: int, name: str) -> pd.DataFrame:
        return pd.read_pickle(self._table_path(year, name))

    def save(self, year: int, name: str, table: pd.DataFrame) -> Path:
        path = self._table_path(year, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        table.to_pickle(path)
        return path

    def save_text(self, name: str, text: str) -> Path:
        path = self._root / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _table_path(self, year: int, name: str) -> Path:
        return self._root / str(year) / f"{name}.pkl"
