"""券種を表す値。"""

from __future__ import annotations

from enum import Enum

from yosou.shared.repository import PAYOUT_TABLES


class BetType(Enum):
    """荒れ具合を出す券種（設計書 10）。値は人が読む名前で、``--bet`` の書き方と、出力の表の列の値にそのまま使う。

    ``key`` は共通の ``RacePayoutRepository`` が読む払戻の列の名前の頭（``win_yen`` など）で、モデルの置き場所の
    フォルダ名にもなる。
    """

    WIN = "単勝"
    QUINELLA = "馬連"
    TRIO = "3連複"
    TRIFECTA = "3連単"

    @property
    def label(self) -> str:
        """人が読む名前（単勝・馬連・3連複・3連単）。"""
        return self.value

    @property
    def key(self) -> str:
        """払戻の列の名前の頭と、モデルのフォルダ名（win・quinella・trio・trifecta）。"""
        return _KEYS[self]

    @property
    def column_name(self) -> str:
        """目的変数の列の名前（例: 荒れ具合（単勝））。"""
        return f"荒れ具合（{self.label}）"

    @classmethod
    def parse(cls, text: str) -> BetType:
        """``単勝`` のような書き方から券種を返す。知らなければ ``ValueError``。"""
        for bet in cls:
            if bet.label == text.strip():
                return bet
        raise ValueError(f"知らない券種です: {text}（{BET_CHOICES}）")


#: 券種 → 払戻の列の名前の頭。共通の ``PAYOUT_TABLES`` の鍵と同じでなければならない。
_KEYS: dict[BetType, str] = {
    BetType.WIN: "win", BetType.QUINELLA: "quinella", BetType.TRIO: "trio", BetType.TRIFECTA: "trifecta",
}
if set(_KEYS.values()) != set(PAYOUT_TABLES):
    raise ImportError("券種の鍵が、共通の払戻の表の鍵と合っていません")

#: 券種の書き方の案内（コマンドの説明と、誤りの文面に使う）。
BET_CHOICES = " / ".join(bet.label for bet in BetType)
