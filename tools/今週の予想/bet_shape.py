"""買い目をまとめた1つの形（フォーメーション・流し・ボックスなど）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BetShape:
    """``text`` は投票の画面でそのまま選べる形の書き方、``points`` はその形で買う点数。

    例: ``BetShape("フォーメーション 10 − 2・6・7 − 1・2・5・6・7・11・16", 15)``。
    """

    text: str
    points: int
