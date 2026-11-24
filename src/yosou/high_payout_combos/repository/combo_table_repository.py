"""券種ごと・年ごとの組の表のファイルを読み書きする。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from yosou.shared.betting import TicketType

from .combo_table_writer import ComboTableWriter


class ComboTableRepository:
    """組の表（材料・出発点・当たったか・払戻）を ``<folder>/<券種の英名>_<年>.parquet`` に置く。

    例: 3連複の 2024年は ``trio_2024.parquet``。JV-Data から作ったもので公開しないので、``folder`` は Git の対象外（``reports/``）にする。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def path(self, ticket_type: TicketType, year: int) -> Path:
        return self._folder / f"{ticket_type.key}_{year}.parquet"

    def exists(self, ticket_type: TicketType, year: int) -> bool:
        return self.path(ticket_type, year).exists()

    def years(self, ticket_type: TicketType) -> list[int]:
        """その券種の表のある年（古い順）。"""
        return sorted(int(path.stem.rsplit("_", 1)[1]) for path in self._folder.glob(f"{ticket_type.key}_*.parquet"))

    def writer(self, ticket_type: TicketType, year: int) -> ComboTableWriter:
        """その券種・年の表を、月ごとに足して書く書き手。前に作った表があれば、閉じたときに置き換わる。"""
        return ComboTableWriter(self.path(ticket_type, year))

    def load(self, ticket_type: TicketType, year: int, columns: Sequence[str] | None = None) -> pd.DataFrame:
        """その券種・年の表。``columns`` を渡すと、その列だけ読む。無ければ ``FileNotFoundError``。"""
        path = self.path(ticket_type, year)
        if not path.exists():
            raise FileNotFoundError(f"組の表がありません: {path}（先に tables で作ってください）")
        return pd.read_parquet(path, columns=list(columns) if columns is not None else None)
