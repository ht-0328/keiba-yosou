"""利用者の規則を基準にしたときの当たり具合の値。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserRuleResult:
    """利用者の規則（1番人気 4.0倍以上かつ 2〜5番人気の最大オッズ 10倍未満 なら荒れる）を「中荒れ以上」の予想とみなしたときの値
    （設計書 16 の 3）。

    - ``rows``: 測ったレースの数。
    - ``hits``: 規則に当てはまったレースの数。
    - ``precision``: 当てはまったレースのうち、実際に中荒れ以上だった割合（当てはまるレースが無ければ NaN）。
    - ``recall``: 実際に中荒れ以上だったレースのうち、規則に当てはまった割合（中荒れ以上が無ければ NaN）。
    - ``base_rate``: 全レースのうち中荒れ以上だった割合（規則を使わないときの割合）。
    """

    rows: int
    hits: int
    precision: float
    recall: float
    base_rate: float
