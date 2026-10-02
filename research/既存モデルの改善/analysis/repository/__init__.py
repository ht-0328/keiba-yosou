"""この研究が元DB から読むもの（1 SQL = 1クラス。元DB は読むだけ）。

| クラス | 読むもの |
|---|---|
| ``RunnerHistoryRepository`` | 2016年からの全出走（1行 = 1頭）の、材料の実験に使う列（着順・走破タイム・4角の位置・オッズ・騎手・調教師・血統） |
| ``ComboPoolSupportRepository`` | 組の全部の馬に配る券種（複勝・馬連・ワイド・3連複）の確定オッズから、馬ごとの支持（その馬を含む組の確率の和） |
| ``FirstHorsePoolSupportRepository`` | 1着の馬だけを見る券種（馬単・3連単）の確定オッズから、馬ごとの支持（その馬が1着の組の確率の和） |
| ``PoolSpec`` | 1つの券種の、表の名前・組の形・値段の式・作る列の名前 |

確定オッズ・払戻を券種ごとに読むのは、研究「馬券の買い方の検証」のリポジトリ（``FinalOddsRepository``・``PayoutRepository``）を使う。
"""

from .combo_pool_support_repository import ComboPoolSupportRepository
from .first_horse_pool_support_repository import FirstHorsePoolSupportRepository
from .pool_spec import POOL_SPECS, PoolSpec
from .runner_history_repository import RunnerHistoryRepository

__all__ = [
    "RunnerHistoryRepository", "ComboPoolSupportRepository", "FirstHorsePoolSupportRepository", "PoolSpec", "POOL_SPECS",
]
