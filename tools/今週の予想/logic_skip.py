"""AI＋ロジック予想が印の買い目を見送る理由（どのロジックに当たったか）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogicSkip:
    """``name`` はロジックの短い名前（展開・クラス）、``reason`` は見送る理由の文。"""

    name: str
    reason: str
