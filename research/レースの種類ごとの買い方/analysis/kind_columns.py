"""学習データの評価用の列に、レースの種類（上のクラス・ハンデ戦の区分と重量種別）を足す。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import RACE_ID, TrainingData

#: 評価用の列の名前。区分は「分ける」案の学習の分け方、重量種別は「材料を足す」案の材料のもと。
SEGMENT_COLUMN, WEIGHT_TYPE_COLUMN = "種類の区分", "重量種別"
#: 区分の値。上のクラス（3勝・オープン・L・重賞）かハンデ戦のレースと、それ以外。
TARGET_SEGMENT, OTHER_SEGMENT = "上のクラス・ハンデ", "それ以外"


class KindColumns:
    """``RaceKinds`` の表（``race_id``・``class_group``・``handicap``・``weight_type``）から、学習データの評価用の列に
    ``SEGMENT_COLUMN`` と ``WEIGHT_TYPE_COLUMN`` を足す。種類の分からないレース（障害など）の区分は「それ以外」、重量種別は空にする。
    例: 3勝クラスの定量のレース → 区分「上のクラス・ハンデ」・重量種別「定量」。
    """

    def __init__(self, kinds: pd.DataFrame) -> None:
        table = kinds.assign(race_id=kinds["race_id"].astype(str))
        target = (table["class_group"] == "上のクラス") | table["handicap"].astype(bool)
        self._segment = pd.Series(target.map({True: TARGET_SEGMENT, False: OTHER_SEGMENT}).to_numpy(), index=table["race_id"])
        self._weight = pd.Series(table["weight_type"].to_numpy(), index=table["race_id"])

    def add(self, data: TrainingData) -> TrainingData:
        race = data.ids[RACE_ID].astype(str)
        evaluation = data.evaluation.assign(**{
            SEGMENT_COLUMN: race.map(self._segment).fillna(OTHER_SEGMENT).to_numpy(),
            WEIGHT_TYPE_COLUMN: race.map(self._weight).fillna("").to_numpy(),
        })
        return replace(data, evaluation=evaluation)
