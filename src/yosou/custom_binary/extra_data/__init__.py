"""特徴量が使う追加の元データ。特徴量の ``sources`` に名前を書くと、その特徴量が選ばれたときだけ読んで、出走の行に列を足す。"""

from .extra_data_loader import ExtraDataLoader
from .pool_probability_source import PoolProbabilitySource

__all__ = ["ExtraDataLoader", "PoolProbabilitySource"]
