"""モデルを分ける単位（芝ダート × 距離。設計書 08 の 3）。

| 名前 | 仕事 |
|---|---|
| ``CourseUnitMap`` | 芝ダと距離から単位を決める。1番人気の少ない距離は、近い距離とまとめる |
"""

from .course_unit_map import DISTANCE, SURFACE, CourseUnitMap

__all__ = ["CourseUnitMap", "SURFACE", "DISTANCE"]
