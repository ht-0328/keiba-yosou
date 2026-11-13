"""回顧の DB の表3「馬の回顧ノート」から、不利のあった馬（出遅れ・展開が向かなかった・バイアスと逆）を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from .race_review_repository import DEFAULT_REVIEW_DB

_TABLE = "馬の回顧ノート"


@dataclass(frozen=True)
class DisadvantageNoteRepository:
    """1行 = 不利のあった1頭の走。列は race_id・horse_id・disadvantage（不利の種類）・degree（程度）。
    人気馬が負けた理由を事例の表に添えるためだけに使う。DB が無ければ空の表を返す。"""

    path: Path = DEFAULT_REVIEW_DB

    def load(self) -> pd.DataFrame:
        if not Path(self.path).exists():
            return pd.DataFrame(columns=["race_id", "horse_id", "disadvantage", "degree"])
        sql = f'SELECT race_id, horse_id, "不利の種類" AS disadvantage, "程度" AS degree FROM "{_TABLE}"'
        with duckdb.connect(str(self.path), read_only=True) as con:
            frame = con.execute(sql).df()
        return frame.astype({"race_id": str, "horse_id": str})
