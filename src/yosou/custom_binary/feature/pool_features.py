"""券種オッズの特徴量の一覧（券種ごとの確率6個と、単勝との差6個）。"""

from ..repository import POOLS
from .pool_gap import PoolGap
from .pool_probability import PoolProbability


def pool_features() -> tuple:
    return (*(PoolProbability(spec) for spec in POOLS), *(PoolGap(spec) for spec in POOLS))
