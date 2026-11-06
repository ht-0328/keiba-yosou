"""馬連・3連複の組の表の置き場所（券種ごとの pkl。作るのに 20〜30分かかるので、買い方を試すたびに作り直さない）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .ticket_tables_builder import TICKETS


class QuinellaTrioTablesStore:
    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def path(self, ticket: str) -> Path:
        return self._folder / f"{ticket}.pkl"

    def save(self, tables: dict[str, pd.DataFrame]) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        for ticket, table in tables.items():
            table.to_pickle(self.path(ticket))

    def load(self) -> dict[str, pd.DataFrame]:
        missing = [ticket for ticket in TICKETS if not self.path(ticket).is_file()]
        if missing:
            raise FileNotFoundError(f"組の表がありません（{'・'.join(missing)}）。先に --build で作ってください: {self._folder}")
        return {ticket: pd.read_pickle(self.path(ticket)) for ticket in TICKETS}
