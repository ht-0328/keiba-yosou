"""予測と事実を、1行 = 1レースの表（races）と 1行 = 1頭の表（runners）にまとめる。

| クラス | 仕事 |
|---|---|
| ``RaceMaterials`` | races と runners の2表を持つ値。レースごとの runners を引く |
| ``RunnerTableBuilder`` | 3つの1頭ごとの予測（近走と適性・人気馬・穴馬）を (レースID, 馬番) で結合し、英語の列名にする |
| ``RaceTableBuilder`` | レースの属性 + 荒れ具合（券種ごとの中荒れ以上の確率）+ 本命とその危険確率 + 重賞か + 開催週 |
| ``RaceWeek`` | 開催日 → 開催週の鍵（土曜始まり。土日と月曜の振替を同じ週にする） |

列の名前は ``analysis/column_names.py``。
"""

from .race_materials import RaceMaterials
from .race_table_builder import GRADED_CODES, RaceTableBuilder
from .race_week import RaceWeek
from .runner_table_builder import RunnerTableBuilder

__all__ = ["RaceMaterials", "RunnerTableBuilder", "RaceTableBuilder", "GRADED_CODES", "RaceWeek"]
