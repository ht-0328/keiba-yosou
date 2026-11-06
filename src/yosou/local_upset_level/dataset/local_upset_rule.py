"""地方の券種ごとの荒れ具合の線引き。"""

from __future__ import annotations

from yosou.upset_level.dataset import BetType, UpsetLevelRule

#: 地方の線引き（中荒れ・大荒れ・超荒れの最初の額。100円あたりの円）。3連単は利用者の帯（1万・10万・100万）。
#: ほかの券種は、2019年以降の地方の全レースで 3連単と同じ割合（固い 5割・中荒れ 4割・大荒れ 1割・超荒れ 1% 弱）になる額を丸めたもの（設計書 10）。
LOCAL_THRESHOLDS: dict[BetType, tuple[int, int, int]] = {
    BetType.WIN: (300, 1_500, 5_000),
    BetType.QUINELLA: (1_000, 6_000, 30_000),
    BetType.TRIO: (2_000, 15_000, 100_000),
    BetType.TRIFECTA: (10_000, 100_000, 1_000_000),
}


class LocalUpsetRule(UpsetLevelRule):
    """中央の ``UpsetLevelRule`` と同じ決め方で、線引きだけ地方の額にしたもの。目的変数と過去の荒れ率（E）の両方がこれを使う。"""

    def __init__(self) -> None:
        super().__init__(LOCAL_THRESHOLDS)
