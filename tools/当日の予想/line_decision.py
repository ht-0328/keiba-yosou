"""期待値の線を選んだ結果（1つのモデルぶん）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineDecision:
    """``line`` は買いにする期待値の線。届く線が無ければ None（そのモデルは「買い」を出さず「参考」として出す）。"""

    line: float | None
    reason: str
