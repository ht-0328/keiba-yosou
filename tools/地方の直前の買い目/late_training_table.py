"""学習用の表（1頭1行。材料の列と結果の列）を読み、特徴量と答えの列を足す。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .late_columns import FINAL_ODDS, MATERIAL_COLUMNS, RACE_DATE, WIN_TEACHER, WON
from .late_features import LateFeatures
from .late_targets import LateTargets

#: 既定の置き場所（Git 対象外）。研究「地方の直前の材料で買う」の analysis/training_table.py が書く。
PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = PROJECT / "reports" / "地方の直前の買い目" / "学習用の表.pkl"


class LateTrainingTable:
    """表が無ければ ``FileNotFoundError``、列が足りなければ ``ValueError``。開催日は日付の型にそろえ、開催日の順に並べて返す。"""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self._path = path

    def load(self) -> pd.DataFrame:
        if not self._path.is_file():
            raise FileNotFoundError(f"学習用の表がありません: {self._path}。先に research/地方の直前の材料で買う/analysis/training_table.py で作ってください")
        table = pd.read_pickle(self._path)
        missing = [column for column in (*MATERIAL_COLUMNS, FINAL_ODDS, WON, WIN_TEACHER) if column not in table.columns]
        if missing:
            raise ValueError(f"学習用の表に列が足りません: {'・'.join(missing)}")
        rows = LateTargets().attach(LateFeatures().build(table))
        rows[RACE_DATE] = pd.to_datetime(rows[RACE_DATE])
        return rows.sort_values(RACE_DATE, kind="stable").reset_index(drop=True)
