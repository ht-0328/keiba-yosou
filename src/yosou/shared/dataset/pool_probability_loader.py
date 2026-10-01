"""券種オッズから見た馬ごとの確率を、6つの券種ぶん1つの表にする。"""

from __future__ import annotations

import duckdb
import pandas as pd

from ..repository import POOLS, AllHorsesPoolRepository, FirstHorsePoolRepository, PoolSpec

#: 出走の行と突き合わせる鍵。
POOL_KEY = ["race_id", "horse_no"]


class PoolProbabilityLoader:
    """券種（3連単・馬単・3連複・馬連・ワイド・複勝）ごとのリポジトリを呼び、``POOLS`` の列を1つずつ持つ表にする。

    1着の馬だけを見る券種（馬単・3連単）は ``FirstHorsePoolRepository``、組の全部の馬に配る券種は
    ``AllHorsesPoolRepository`` で読む。発売の無い券種の馬は欠損値。SQL は持たない。
    custom_binary の追加の元データ「券種オッズ」と、近走と適性の予想の当日版（まとまり N）が使う。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._first_horse = FirstHorsePoolRepository(con)
        self._all_horses = AllHorsesPoolRepository(con)

    def read(self, scope_relation: str) -> pd.DataFrame:
        """``scope_relation``（``race_id`` の列を持つ関係）のレースの表。列は ``race_id``・``horse_no`` と ``POOLS`` の列。"""
        frames = [self._repository_of(spec).read(spec, scope_relation).set_index(POOL_KEY) for spec in POOLS]
        return pd.concat(frames, axis=1).reset_index()

    def _repository_of(self, spec: PoolSpec) -> FirstHorsePoolRepository | AllHorsesPoolRepository:
        """その券種を読むリポジトリ。"""
        return self._first_horse if spec.first_horse_only else self._all_horses
