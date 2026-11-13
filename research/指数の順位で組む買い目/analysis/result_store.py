"""レースごとの精算の表を reports に書き、読み戻す。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: 精算の表の列（1行 = 1レース × 1つの形）。``timing`` は 当日・前日、``ranking`` は順位の決め方、``group`` は 形・上位5頭BOX。
COLUMNS: tuple[str, ...] = ("timing", "ranking", "group", "formation", "ticket", "race_id", "race_date", "points", "payout", "hit")
#: 置き場所のフォルダ名。
SETTLED_FOLDER = "精算"
BASELINE_FOLDER = "比べる相手"


class ResultStore:
    """精算の表（形ごと）と比べる相手の表を、``folder``（Git 対象外の reports）に parquet で置く。

    精算は ``精算/<時点>-<順位の決め方>.parquet``、比べる相手は ``比べる相手/<時点>.parquet``。
    """

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)

    def save_settled(self, table: pd.DataFrame, timing: str, ranking: str) -> Path:
        path = self.folder / SETTLED_FOLDER / f"{timing}-{ranking}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        table[list(COLUMNS)].to_parquet(path, index=False)
        return path

    def load_settled(self) -> pd.DataFrame:
        """置いてある精算の表を全部つないだもの（無ければ空）。"""
        paths = sorted((self.folder / SETTLED_FOLDER).glob("*.parquet"))
        if not paths:
            return pd.DataFrame(columns=list(COLUMNS))
        return pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)

    def save_baseline(self, table: pd.DataFrame, timing: str) -> Path:
        path = self.folder / BASELINE_FOLDER / f"{timing}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        table.to_parquet(path, index=False)
        return path

    def load_baselines(self) -> dict[str, pd.DataFrame]:
        """時点 → 比べる相手の表。"""
        return {path.stem: pd.read_parquet(path) for path in sorted((self.folder / BASELINE_FOLDER).glob("*.parquet"))}
