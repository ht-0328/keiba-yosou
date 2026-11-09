"""成績の表の1行の決め方（名前・券種・合わせる形・集計金額）。"""

from __future__ import annotations

from dataclasses import dataclass

from .payout_floor import PayoutFloor


@dataclass(frozen=True)
class RowSpec:
    """成績の表の1行。``members`` の形（精算の表の ``formation`` の値）をレースごとに合わせて数える。

    1つの形だけなら形そのもの、複数なら合計の行。``floors`` は集計金額（合計の行は無し）。
    """

    label: str
    ticket: str
    members: tuple[str, ...]
    floors: tuple[PayoutFloor, ...] = ()

    @property
    def is_total(self) -> bool:
        return len(self.members) > 1
