"""全レースで学んだ手本の予測から、重賞の行だけを取り出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID

#: 行を突き合わせる鍵。
_KEY = [RACE_ID, HORSE_ID]
#: 重賞の行だけにした手本の予測を保存するときに、作り方の名前の後ろに付ける（例 general-race_day-stakes）。
#: 道具「印の成績」で、専用モデルと同じ重賞のレースについて印と買い目の成績を比べるためのもの。
STAKES_ROWS_SUFFIX = "-stakes"


class StakesRowFilter:
    """手本（全レースで学ぶ）の予測の表のうち、重賞だけの表にある出走（レースID・馬ID）の行だけを残す。

    「手本を重賞だけに使ったとき」の当たり具合を、作り直した専用モデルと同じ行で測るためのもの。
    ``stakes_ids`` は重賞だけの学習データの ID 列。
    """

    def __init__(self, stakes_ids: pd.DataFrame) -> None:
        keys = stakes_ids[_KEY].astype(str).drop_duplicates()
        self._keys = keys.reset_index(drop=True)

    def apply(self, predictions: pd.DataFrame) -> pd.DataFrame:
        """``predictions`` の列はそのまま、重賞の行だけ。"""
        typed = predictions.assign(**{column: predictions[column].astype(str) for column in _KEY})
        return typed.merge(self._keys, on=_KEY, how="inner").reset_index(drop=True)
