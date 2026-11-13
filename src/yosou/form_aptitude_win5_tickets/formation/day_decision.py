"""その日の WIN5 を買うかどうか（買うなら、多く買う日か少なく買う日か）。"""

from __future__ import annotations

from enum import Enum


class DayDecision(Enum):
    """買う（多く）・買う（少なく）・見送り（設計書 15 の 13）。

    判断用の買い目の日の期待値が買う日の線未満なら見送り（買い目と当たる確率は同じ形で出す）。線以上なら買う日で、本命の確率の積が
    多く買う日の線以上なら「買う（多く）」、未満なら「買う（少なく）」。
    """

    BUY_LARGE = "買う（多く）"
    BUY_SMALL = "買う（少なく）"
    SKIP = "見送り"

    @property
    def label(self) -> str:
        return self.value

    @property
    def buys(self) -> bool:
        """買う日か（多くでも少なくでも）。"""
        return self is not DayDecision.SKIP

    @property
    def tier_label(self) -> str:
        """段階の名前（``多く``・``少なく``・``見送り``）。"""
        return {DayDecision.BUY_LARGE: "多く", DayDecision.BUY_SMALL: "少なく", DayDecision.SKIP: "見送り"}[self]

    @classmethod
    def parse(cls, text: str) -> DayDecision:
        """記録の「判断」の文字から。古い記録（段階の無い「買う」）は「買う（少なく）」でも「買う（多く）」でもないので、
        買う日としてだけ読みたいときは ``buys_text`` を使う。知らなければ ``ValueError``。"""
        for each in cls:
            if each.value == text:
                return each
        raise ValueError(f"知らない判断です: {text}")

    @classmethod
    def buys_text(cls, text: str) -> bool:
        """記録の「判断」の文字が買う日か（``見送り`` 以外は買う日。古い記録の「買う」も買う日）。"""
        return text != cls.SKIP.value
