"""追加の元データ「券種オッズ」。券種ごとのオッズから見た馬ごとの確率。"""

import duckdb
import pandas as pd

from yosou.shared.dataset import POOL_KEY, PoolProbabilityLoader
from yosou.shared.repository import POOLS

#: 出走の行と突き合わせる鍵。
KEY = POOL_KEY


class PoolProbabilitySource:
    """券種（3連単・馬単・3連複・馬連・ワイド・複勝）ごとに、``POOLS`` の列を1つずつ作る。発売の無い券種の馬は欠損値。

    読むのは、近走と適性の予想と共通の ``PoolProbabilityLoader``（``yosou.shared.dataset``）。
    """

    name = "券種オッズ"
    columns = tuple(spec.column for spec in POOLS)

    def read(self, con: duckdb.DuckDBPyConnection, scope_relation: str) -> pd.DataFrame:
        return PoolProbabilityLoader(con).read(scope_relation)
