"""レース単位の表を、事例を見るための1つの表（1行 = 1レース）にする。"""

from __future__ import annotations

import pandas as pd

from 共通 import codes

from yosou.shared.dataset import RACE_DATE, RACE_ID, TrainingData

from .obi_rules import payout_class
from .race_table_loader import TRIFECTA_YEN

#: 足す列の名前。
YEAR, PAYOUT_CLASS, CLASS_NAME = "年", "払戻の段", "クラス名"
#: クラスの並び順 → クラス名（特徴量のクラスは並び順の数。格付けの無い重賞は G3 と同じ 8 に付け直してある）。
_CLASS_NAMES: dict[float, str] = {float(order): name for name, order in codes.CLASS_ORDER.items() if name != "重賞"}


def race_frame(data: TrainingData) -> pd.DataFrame:
    """ID（レースID・開催日）・特徴量・評価用の列を横に並べ、年・払戻の段（帯・大荒れ・それ以外）・クラス名を足す。

    3連単の払戻が無いレース（発売の無いレース）は落とす。ID の競馬場・レース番号は特徴量の側にあるので写さない。
    """
    ids = data.ids[[RACE_ID, RACE_DATE]]
    frame = pd.concat([ids, data.features, data.evaluation], axis=1)
    frame = frame[frame[TRIFECTA_YEN].notna()]
    return frame.assign(**{
        YEAR: frame[RACE_DATE].dt.year,
        PAYOUT_CLASS: frame[TRIFECTA_YEN].map(payout_class),
        CLASS_NAME: frame["クラス"].map(_CLASS_NAMES),
    })
