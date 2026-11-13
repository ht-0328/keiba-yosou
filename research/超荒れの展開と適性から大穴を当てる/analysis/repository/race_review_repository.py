"""回顧の DB（``reports/回顧/review.duckdb``）の表2「レースの回顧」から、結果のペースとその日のバイアスの傾きを読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

#: 回顧の DB の置き場所（道具「回顧」と道具「今週の予想」が書く。Git の対象外）。
DEFAULT_REVIEW_DB = Path(__file__).resolve().parents[4] / "reports" / "回顧" / "review.duckdb"
_TABLE = "レースの回顧"


@dataclass(frozen=True)
class RaceReviewRepository:
    """1行 = 1レース。列は race_id・pace（結果のペース: ハイ・平均・スロー。前3ハロンを同じ条件の基準と比べて分けたもの）・
    tilt_inner（その日の内の傾き。正なら内が市場の見立てより来ている）・tilt_front（その日の前の傾き。正なら前が来ている）。

    傾きは、その日のほかのレースと前の日のレースから出したもので、そのレース自身は含まない（設計書「買うレースと買い目を決める」08 の 3）。
    DB が無ければ空の表を返す（ほかの表は作れるように）。
    """

    path: Path = DEFAULT_REVIEW_DB

    def load(self) -> pd.DataFrame:
        if not Path(self.path).exists():
            return pd.DataFrame(columns=["race_id", "pace", "tilt_inner", "tilt_front"])
        sql = (f'SELECT race_id, "結果のペース" AS pace, "当日の内の傾き" AS tilt_inner, "当日の前の傾き" AS tilt_front '
               f'FROM "{_TABLE}"')
        with duckdb.connect(str(self.path), read_only=True) as con:
            frame = con.execute(sql).df()
        return frame.astype({"race_id": str, "tilt_inner": "float64", "tilt_front": "float64"})
