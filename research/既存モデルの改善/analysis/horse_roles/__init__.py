"""3つの予想から、馬ごとの期待値と役割（消・軸・◎、人気か穴か）を決める（利用者と決めた買い方）。

| 名前 | 仕事 |
|---|---|
| ``HorseValues`` | 馬ごとの単勝・複勝の期待値、人気か穴か、人気馬の危険度を足す |
| ``RoleAssigner`` | 消（本当に危険な1番人気）・軸（安心な馬。1頭か2頭）・◎（単勝の期待値がいちばん高い馬）を決める |

列の名前は ``role_columns.py``。
"""

from .horse_values import HorseValues
from .role_assigner import RoleAssigner
from .role_columns import AXIS, DANGER, EXCLUDED, HONMEI, PLACE_VALUE, POPULAR, WIN_VALUE

__all__ = ["HorseValues", "RoleAssigner", "AXIS", "DANGER", "EXCLUDED", "HONMEI", "PLACE_VALUE", "POPULAR", "WIN_VALUE"]
