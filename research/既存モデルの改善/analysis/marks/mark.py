"""予想の印。"""

from __future__ import annotations

from enum import Enum

#: 1頭ごとの表の、印の列の名前。
MARK = "印"


class Mark(Enum):
    """予想の印。値は表に出す記号。

    | 印 | 意味 | 頭数 |
    |---|---|---|
    | ◎ 本命 | いちばん来ると見る馬 | 1 |
    | ○ 対抗 | 2番手 | 1 |
    | ▲ 単穴 | 3番手 | 1 |
    | △ 連下 | 2〜3着なら来る | 3 |
    | ☆ 穴 | 人気はないが、複勝を買う価値がある | 1 |
    | 注 注意 | 印の圏外だが、オッズの見立てより来ると見ている | 1 |
    """

    HONMEI = "◎"
    TAIKOU = "○"
    TANANA = "▲"
    RENSHITA = "△"
    ANA = "☆"
    CHUI = "注"
