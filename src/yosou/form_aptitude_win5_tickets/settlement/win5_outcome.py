"""過去の WIN5 の1回の結果を表す値。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Win5Outcome:
    """1回の WIN5 の、当たり組（5頭の馬番の並び）と100円あたりの払戻（同着なら2つ以上）、的中無の印、
    対象レースごとの出走取消・競走除外の馬番（発売の順に5つ）、発売票数、キャリーオーバー金額初期（円）。"""

    race_date: str
    winners: tuple[tuple[tuple[int, ...], int], ...]
    no_hit: bool
    scratched: tuple[frozenset[int], ...]
    votes: int
    carry: int
