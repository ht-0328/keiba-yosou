"""近さの点数の列の名前。"""

from ..dataset import GROUPS

#: グループの名前 → そのグループへの近さの点数の列の名前（0〜100。大きいほど近い）。
SCORE_COLUMNS: dict[str, str] = {group: f"{group}の近さ" for group in GROUPS}
#: 単位の名前の列。
UNIT = "単位"
