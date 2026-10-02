"""特徴量が使う追加の元データ。特徴量の ``sources`` に名前を書くと、その特徴量が選ばれたときだけ読んで、出走の行に列を足す。

| 名前 | 仕事 |
|---|---|
| ``ExtraDataLoader`` | 選んだ特徴量が使う追加の元データを読み、出走の行に列を足す。使える元データは ``SOURCES`` |
| ``PoolProbabilitySource`` | 追加の元データ「券種オッズ」。6つの券種の確率を1つの表にする |
| ``RaceRelation`` | 予想する1レースだけを対象にする関係（SQL） |
"""

from .extra_data_loader import ExtraDataLoader
from .pool_probability_source import PoolProbabilitySource
from .race_relation import RaceRelation

__all__ = ["ExtraDataLoader", "PoolProbabilitySource", "RaceRelation"]
