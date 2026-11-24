"""馬ごとの表を parquet に書く。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 高配当の買い目.folders import DEFAULT_HORSES_FOLDER
from 高配当の買い目.horse_table_columns import KEY_COLUMNS, RACE_DATE


class HorseTableStore:
    """馬ごとの表（``HorseTableSelector.select`` の戻り値）を parquet に書く。

    既定の名前は ``<置き場所>/<最初の年>-<最後の年>.parquet``（例: 2020年〜2026年の行なら ``2020-2026.parquet``）。
    予想のパッケージは置き場所の parquet を全部読んでつなぎ、同じ (race_id, horse_no) が2つのファイルにあると誤りにする。
    それで、書く先と同じフォルダのほかの parquet に同じ出走があれば、書かずに誤りにする（古いファイルを消すか、別の場所に書く）。
    """

    def __init__(self, folder: Path = DEFAULT_HORSES_FOLDER) -> None:
        self._folder = Path(folder)

    def default_path(self, table: pd.DataFrame) -> Path:
        years = pd.to_datetime(table[RACE_DATE]).dt.year
        return self._folder / f"{int(years.min())}-{int(years.max())}.parquet"

    def save(self, table: pd.DataFrame, path: Path) -> Path:
        if table.empty:
            raise ValueError("馬ごとの表に行がありません（開催日の範囲と予測のファイルを確かめてください）")
        path = Path(path)
        overlapping = [other.name for other in self._neighbors(path) if self._overlaps(other, table)]
        if overlapping:
            raise ValueError(f"同じフォルダの {', '.join(overlapping)} に同じ出走の行があります。古いファイルを消すか、--out で別の場所に書いてください: {path.parent}")
        path.parent.mkdir(parents=True, exist_ok=True)
        table.to_parquet(path, index=False)
        return path

    @staticmethod
    def _neighbors(path: Path) -> list[Path]:
        """書く先と同じフォルダの、ほかの parquet。"""
        if not path.parent.is_dir():
            return []
        return sorted(other for other in path.parent.glob("*.parquet") if other.resolve() != path.resolve())

    @staticmethod
    def _overlaps(other: Path, table: pd.DataFrame) -> bool:
        """``other`` に、``table`` と同じ (race_id, horse_no) の行があるか。"""
        keys = pd.read_parquet(other, columns=list(KEY_COLUMNS)).astype({KEY_COLUMNS[0]: str, KEY_COLUMNS[1]: int})
        wanted = table[list(KEY_COLUMNS)].astype({KEY_COLUMNS[0]: str, KEY_COLUMNS[1]: int})
        return not keys.merge(wanted, on=list(KEY_COLUMNS), how="inner").empty
