"""勝負するレースを選ぶための、レース単位の表を作る。"""

from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID

from ..horse_roles import EXCLUDED
from .candidate_columns import RACE
from .race_columns import FAVORITE_EXCLUDED, GRADED, UPSET, UPSET_PROBABILITY


class RaceTableBuilder:
    """役割の付いた1頭ごとの表から、1行 = 1レースの表（開催日・重賞か・1番人気を消したか・荒れそうか）を作る。

    ``graded`` は重賞のレースID（研究「馬券の買い方の検証」の ``RaceFactRepository`` のグレードコード A〜D）。
    ``upset`` はレースID → 荒れそうな確率、``upset_line`` はそれ以上を「荒れそう」とする線。
    """

    def build(self, horses: pd.DataFrame, graded: Collection[str], upset: pd.Series, upset_line: float) -> pd.DataFrame:
        grouped = horses.groupby(RACE_ID, sort=False)
        races = pd.DataFrame({
            RACE: [str(race_id) for race_id in grouped.groups],
            RACE_DATE: grouped[RACE_DATE].first().to_numpy(),
            FAVORITE_EXCLUDED: grouped[EXCLUDED].any().to_numpy(),
        })
        probability = races[RACE].map(upset)
        return races.assign(**{
            GRADED: races[RACE].isin(set(graded)), UPSET_PROBABILITY: probability, UPSET: (probability >= upset_line).fillna(False),
        })
