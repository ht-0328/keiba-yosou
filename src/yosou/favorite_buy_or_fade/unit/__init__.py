"""モデルを分ける単位（芝ダート × 距離。設計書 08 の 3）。

| 名前 | 仕事 |
|---|---|
| ``CourseUnitMap`` | 芝ダと距離から単位を決める。1番人気の少ない距離は、近い距離とまとめる |
| ``SingleUnitMap`` | 単位で分けない（全部を1つの単位にする）ときの単位の決め方。方針の ``split = "なし"`` |
"""

from .course_unit_map import DISTANCE, SURFACE, CourseUnitMap
from .single_unit_map import WHOLE_UNIT, SingleUnitMap

__all__ = ["CourseUnitMap", "SingleUnitMap", "SURFACE", "DISTANCE", "WHOLE_UNIT"]
