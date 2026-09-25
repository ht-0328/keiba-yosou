"""custom_binary が元DB から読む追加のデータ。1つのクラスが1つの SQL を持つ。"""

from .all_horses_pool_repository import AllHorsesPoolRepository
from .first_horse_pool_repository import FirstHorsePoolRepository
from .pool_spec import POOLS, PoolSpec

__all__ = ["AllHorsesPoolRepository", "FirstHorsePoolRepository", "POOLS", "PoolSpec"]
