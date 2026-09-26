"""予測のたびに、予測用データと予測を書き足す。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


class PredictionArchiveRepository:
    """予測のたびに、予測用データ（特徴量）と予測を ``<root>/<開催日>/<レースID>_<時点>_<予測した時刻>.pkl`` に書く（設計書 15 の 12）。

    同じレース・同じ時点でも上書きせず、予測した時刻を名前に付けて残す。あとで「発走前に実際に手に入っていた材料で、
    どれだけ当たったか」を確かめるためである（元DB は、同じレースの出馬表を新しい版で上書きするので、後から作り直せない）。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def save(self, race_date: str, race_id: str, timing: str, predicted_at: datetime,
             tables: dict[str, pd.DataFrame]) -> Path:
        path = self._root / race_date / f"{race_id}_{timing}_{predicted_at:%Y%m%d%H%M%S}.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.to_pickle(tables, path)
        return path
