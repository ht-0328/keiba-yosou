"""馬ごとの表から、全部のレース（レースIDと開催日）を読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 高配当の買い目.folders import DEFAULT_HORSES_FOLDER
from 高配当の買い目.pick_columns import RACE_DATE, RACE_ID
from 高配当の買い目.race_universe import RaceUniverse


class RaceUniverseReader:
    """馬ごとの表の置き場所（``<置き場所>/*.parquet``。``horses.py`` が書くもの）の全部のファイルから、レースIDと開催日だけを読む。

    1つも無ければ ``FileNotFoundError``（先に ``horses.py`` で作る）。
    """

    def __init__(self, folder: Path = DEFAULT_HORSES_FOLDER) -> None:
        self._folder = Path(folder)

    def read(self) -> RaceUniverse:
        paths = sorted(self._folder.glob("*.parquet"))
        if not paths:
            raise FileNotFoundError(f"馬ごとの表がありません: {self._folder}（先に tools/高配当の買い目/horses.py で作ってください）")
        races = pd.concat([pd.read_parquet(path, columns=[RACE_ID, RACE_DATE]) for path in paths], ignore_index=True)
        return RaceUniverse(races.assign(**{RACE_ID: races[RACE_ID].astype(str)}))
