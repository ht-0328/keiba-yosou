"""馬ごとの表（1行 = 1頭）に、そのレースの払戻の段を付けて、事例を見るための1つの表にする。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID, TrainingData

from .race_frame import PAYOUT_CLASS, YEAR

#: 評価用の列のうち、事例で使うもの。
FINISH, POPULARITY = "確定着順", "確定の単勝人気"
#: 足す列の名前。
IN_TOP3 = "3着以内"


def horse_frame(data: TrainingData, columns: Sequence[str], races: pd.DataFrame) -> pd.DataFrame:
    """ID（レースID・開催日）・``columns`` の特徴量・確定着順と人気を並べ、レースの払戻の段と年、3着以内かを足す。

    ``races`` はレース単位の事例の表（``race_frame`` の結果）。払戻の段の無いレースの馬は落とす。
    """
    ids = data.ids[[RACE_ID, RACE_DATE]]
    frame = pd.concat([ids, data.features[list(columns)], data.evaluation[[FINISH, POPULARITY]]], axis=1)
    frame = frame.merge(races[[RACE_ID, PAYOUT_CLASS]], on=RACE_ID, how="inner")
    return frame.assign(**{YEAR: frame[RACE_DATE].dt.year, IN_TOP3: frame[FINISH].le(3)})
