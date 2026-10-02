"""中間データ（parquet）を読み書きする。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


class CacheStore:
    """``folder`` の下に、名前ごとに1つの parquet を置く。

    pandas の ``to_parquet`` は pyarrow を要するが、この環境には無い。依存を増やさないよう、DuckDB で読み書きする。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = folder

    def write(self, name: str, frame: pd.DataFrame) -> Path:
        self._folder.mkdir(parents=True, exist_ok=True)
        path = self._folder / f"{name}.parquet"
        con = duckdb.connect()
        con.register("frame", frame)
        con.execute(f"COPY frame TO '{path.as_posix()}' (FORMAT parquet)")
        con.close()
        return path

    def read(self, name: str) -> pd.DataFrame:
        path = self._folder / f"{name}.parquet"
        with duckdb.connect() as con:
            return con.execute(f"SELECT * FROM read_parquet('{path.as_posix()}')").df()
