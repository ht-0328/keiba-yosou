"""抑え（荒れる前提）の買い目の候補1つ。本線（今の買い目）は変えず、本線を買う日に、本線とは重ならない組だけを足して買う。"""

from __future__ import annotations

from dataclasses import dataclass

#: 確率の元。
CURRENT, NEW = "今のモデル", "新しい確率"
#: 人気薄の選び方。
BY_SHARE, BY_MARKET = "人気薄の1着の予想の順", "人気の順"


@dataclass(frozen=True)
class HedgeCandidate:
    """荒れそうなレース（段1 の R1 か R3。人気薄の市場合計の大きい順）を最大 ``upset_count`` つ選び、そこを人気薄（10番人気以下）の
    ``longshots`` 頭（``longshot_order`` の順。本線で選んだ馬は除く）に差し替え、ほかのレースは確率の上位から、点数が ``budget`` 以下で
    見積もりの払戻の合計がいちばん大きい頭数にする。荒れそうなレースで本線に無い馬だけを使うので、どの組も本線と重ならない。
    ``source`` は確率の元（ほかのレースの並べ方と、期待値の見積もり）。``line`` は抑えの日の期待値の線（None なら本線を買う日は毎回）。"""

    group: str
    source: str
    longshot_order: str
    upset_count: int
    longshots: int
    budget: int
    line: float | None = None

    @property
    def label(self) -> str:
        line = "本線の日は毎回" if self.line is None else f"抑えの期待値 {self.line:.2f} 以上"
        return f"{self.group}（荒れそうなレース{self.upset_count}つに人気薄{self.longshots}頭・{self.budget}点・{line}）"
