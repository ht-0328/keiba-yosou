"""3つの予想から馬に印を付け、印の組み合わせで買い目を決める（利用者と決めた買い方）。

| 名前 | 仕事 |
|---|---|
| ``Mark`` | 印（◎○▲△☆注） |
| ``MarkMaterial`` | 印を付けるのに使う値（人気馬の危険度・穴馬の複勝の期待値）を足す |
| ``MarkAssigner`` | レースごとに印を付ける（消の馬は外して繰り上げる） |
| ``MarkRule`` | 印の組み合わせで決める、1つの券種の買い目のルール（フォーメーションと着順の入れ替え） |
| ``ALWAYS_RULES``・``COVER_RULES`` | いつも買う（◎から）ルールと、◎が危ういときの押さえ（相手同士）のルール |
"""

from .mark import MARK, Mark
from .mark_assigner import MarkAssigner
from .mark_material import DANGER, LONGSHOT_PLACE_VALUE, MarkMaterial
from .mark_rule import MarkRule
from .mark_rules import ALWAYS_RULES, COVER_RULES, MARK_RULES

__all__ = [
    "Mark", "MARK", "MarkMaterial", "DANGER", "LONGSHOT_PLACE_VALUE", "MarkAssigner", "MarkRule",
    "ALWAYS_RULES", "COVER_RULES", "MARK_RULES",
]
