"""組の表の1つのファイルを、少しずつ書く。"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Self

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

#: 書いている途中のファイルの名前に足す拡張子。書き終えたら外す（途中で止まったファイルを、済んだものと見分けるため）。
_PARTIAL_SUFFIX = ".partial"
_COMPRESSION = "zstd"


class ComboTableWriter:
    """1つの券種・1年ぶんの組の表（Parquet）を、月ごとの表を順に足して書く。

    3連単は1年で数百万行になるので、1年ぶんをメモリに持たずに書く。``with`` で使い、抜けるときに閉じる。
    途中は ``<名前>.partial`` に書き、誤りなく閉じたときだけ本来の名前にする。1行も書かなければファイルを作らない。
    列の並びと型は、最初に書いた表に合わせる。
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._partial = self._path.with_name(self._path.name + _PARTIAL_SUFFIX)
        self._writer: pq.ParquetWriter | None = None
        self.row_count = 0

    def __enter__(self) -> Self:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        return self

    def write(self, table: pd.DataFrame) -> None:
        """表を足す。空の表は書かない。"""
        if table.empty:
            return
        rows = pa.Table.from_pandas(table, preserve_index=False)
        if self._writer is None:
            self._writer = pq.ParquetWriter(self._partial, rows.schema, compression=_COMPRESSION)
        self._writer.write_table(rows.cast(self._writer.schema))
        self.row_count += len(table)

    def __exit__(self, error_type: type[BaseException] | None, error: BaseException | None,
                 traceback: TracebackType | None) -> None:
        if self._writer is None:
            return
        self._writer.close()
        if error_type is None:
            self._partial.replace(self._path)
