"""勝ち切る材料（まとまり Q）の元の記録を、馬と人の2つのリポジトリから読んで1つの表にする。"""

from __future__ import annotations

import duckdb
import pandas as pd

from ..repository import HorseFinishRepository, PeopleFinishRepository, TargetScope

#: 出走の行と突き合わせる鍵。
FINISH_KEY = ["race_id", "horse_id"]


class FinishRecordsLoader:
    """馬の近10走（``HorseFinishRepository``）と騎手・調教師の近1年（``PeopleFinishRepository``）の勝ち切る材料を読み、
    出走ごと（race_id・horse_id）の1つの表にする。SQL は持たない。

    近走と適性の予想の当日のモデル（1着のモデルだけが使う。設計書 15 の 15）が渡す。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._horses = HorseFinishRepository(con)
        self._people = PeopleFinishRepository(con)

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``FINISH_KEY`` と、馬の6列・人の4列。"""
        return self._horses.read(scope).merge(self._people.read(scope), on=FINISH_KEY, how="outer")
