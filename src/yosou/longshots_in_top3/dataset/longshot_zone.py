"""穴馬の区分（中穴・大穴）を表す値。"""

from __future__ import annotations

from enum import Enum


class LongshotZone(Enum):
    """穴馬の区分（設計書 08 の 3）。出力を絞るときにだけ使い、モデルには渡さない（設計書 15 の 5）。

    値は人が読む名前で、``--zone`` の書き方と、出力の表の列の値にそのまま使う。
    どの人気からが大穴かは ``LongshotRule`` が頭数ごとに決める。
    """

    MID = "中穴"
    BIG = "大穴"

    @property
    def label(self) -> str:
        """人が読む名前（中穴・大穴）。"""
        return self.value

    @classmethod
    def parse(cls, text: str) -> LongshotZone:
        """``中穴`` か ``大穴`` から区分を返す。知らなければ ``ValueError``。"""
        for zone in cls:
            if zone.label == text.strip():
                return zone
        raise ValueError(f"知らない区分です: {text}（{ZONE_CHOICES}。省略すると穴馬すべて）")


#: 区分の書き方の案内（コマンドの説明と、誤りの文面に使う）。
ZONE_CHOICES = " / ".join(zone.label for zone in LongshotZone)
