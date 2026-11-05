"""地方の1レースで実際に買う買い目（行）と、買わないときの理由。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocalBets:
    #: 実際に買う行（例 ``単勝 ◎6 テイケイリノ（期待値 1.05）100円``）。
    lines: tuple[str, ...]
    #: 買う行が無いときの理由（例 ``◎ の単勝の期待値 0.90 は 1.00 未満``）。買う行があれば空。
    reasons: tuple[str, ...]

    @property
    def none(self) -> bool:
        return not self.lines

    def text(self) -> list[str]:
        """通知の文に入れる行。"""
        if self.none:
            return [f"買い目: なし（{'。'.join(self.reasons)}）"]
        return ["実際に買う:", *self.lines]
