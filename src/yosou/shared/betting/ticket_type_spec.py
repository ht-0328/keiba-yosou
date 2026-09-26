"""券種ごとの決まりごと（表の名前・組の形）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TicketTypeSpec:
    """1つの券種の、元DB での表し方と買い目の形。``TicketType`` が券種ごとに1つ持つ。

    - ``key``: 英語の短い名前（列名やファイル名の頭に使う。例 ``trio``）。
    - ``horse_count``: 1つの買い目に入る馬の数（単勝 1・馬連 2・3連複 3）。
    - ``is_ordered``: 着順を区別するか（馬単・3連単は True）。
    - ``payout_table``・``combo_column``: 払戻の子の表と、馬番か組番の列。
    - ``odds_parent``・``odds_table``・``has_odds_range``: オッズの親と子の表。複勝・ワイドは最低と最高の2つのオッズを持つ。

    荒れ具合の予想の券種との対応は、予想のパッケージの側に置く（``shared`` は予想のパッケージを参照しない）。
    """

    key: str
    horse_count: int
    is_ordered: bool
    payout_table: str
    combo_column: str
    odds_parent: str
    odds_table: str
    has_odds_range: bool
