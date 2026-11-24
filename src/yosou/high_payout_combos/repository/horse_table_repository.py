"""馬ごとの表のファイルを読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .horse_table_columns import HORSE_NO, RACE_DATE, RACE_ID, STORED_COLUMNS


class HorseTableRepository:
    """``<folder>/*.parquet``（1頭1行。過去レースの、学習に使っていない期間の予測に本番と同じ印を付けた表）を全部読んでつなぐ。

    ファイルごとに列が少し違ってよい。読むのは ``STORED_COLUMNS``（材料づくりの列と開催日）だけ。
    ``race_id`` は16桁の文字列、``race_date`` は日付（時刻なし）にそろえる。同じ（レースID・馬番）が2行あれば ``ValueError``
    （2つのファイルの期間が重なっている）。ファイルが無ければ ``FileNotFoundError``。この表を作るのは別の道具で、ここは読むだけ。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def load(self) -> pd.DataFrame:
        paths = sorted(self._folder.glob("*.parquet"))
        if not paths:
            raise FileNotFoundError(f"馬ごとの表がありません: {self._folder}（*.parquet を置いてください）")
        horses = pd.concat([pd.read_parquet(path, columns=list(STORED_COLUMNS)) for path in paths], ignore_index=True)
        horses[RACE_ID] = horses[RACE_ID].astype(str)
        horses[RACE_DATE] = pd.to_datetime(horses[RACE_DATE]).dt.normalize()
        self._check_unique(horses)
        return horses

    def _check_unique(self, horses: pd.DataFrame) -> None:
        duplicated = horses[horses.duplicated([RACE_ID, HORSE_NO], keep=False)]
        if duplicated.empty:
            return
        first = duplicated.iloc[0]
        raise ValueError(
            f"馬ごとの表に同じ馬が2行あります: レース {first[RACE_ID]} の {first[HORSE_NO]}番（{self._folder} のファイルの期間が重なっていないか確かめてください）"
        )
