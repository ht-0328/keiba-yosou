"""DB のファイルそのものの状態（あるか・大きさ・最終更新）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_BYTES_PER_MB = 1_000_000


@dataclass(frozen=True)
class StoreFile:
    """DuckDB のファイルの状態。最終更新は jvdata-store が最後に書いた時刻の目安（DB を開かずに分かる）。"""

    path: Path
    exists: bool
    size_mb: float
    modified_at: datetime | None

    @classmethod
    def read(cls, path: Path) -> "StoreFile":
        if not path.exists():
            return cls(path, False, 0.0, None)
        stat = path.stat()
        return cls(path, True, round(stat.st_size / _BYTES_PER_MB, 1), datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0))
