"""追加の元データ「券種オッズ」。券種ごとのオッズから見た馬ごとの確率。"""

import duckdb
import pandas as pd

from ..repository import POOLS, AllHorsesPoolRepository, FirstHorsePoolRepository

#: 出走の行と突き合わせる鍵。
KEY = ["race_id", "horse_no"]


class PoolProbabilitySource:
    """券種（3連単・馬単・3連複・馬連・ワイド・複勝）ごとに、``POOLS`` の列を1つずつ作る。発売の無い券種の馬は欠損値。"""

    name = "券種オッズ"
    columns = tuple(spec.column for spec in POOLS)

    def read(self, con: duckdb.DuckDBPyConnection, scope_relation: str) -> pd.DataFrame:
        first_horse = FirstHorsePoolRepository(con)
        all_horses = AllHorsesPoolRepository(con)
        frames = [
            (first_horse if spec.first_horse_only else all_horses).read(spec, scope_relation).set_index(KEY)
            for spec in POOLS
        ]
        return pd.concat(frames, axis=1).reset_index()
