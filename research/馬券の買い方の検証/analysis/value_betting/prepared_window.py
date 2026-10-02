"""1つの区切りの、期待値と消と印を付け終えた材料。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PreparedWindow:
    """1つの区切りについて、戦略に依らず先に計算しておけるもの。

    - ``name``: 区切りの名前。
    - ``test``: テスト期間の1頭ごとの表（期待値・危険度・消・印の列つき）。
    - ``history``: 直前の1年（1つ前の区切りの検証の半年 ＋ この区切りの検証の半年）の1頭ごとの表（期待値・消の列つき）。
    - ``races``: テスト期間のレースごとの表。
    - ``history_is_full_year``: 直前が1年あるか（最初の区切りは半年しか無い）。線を選ぶ点数の下限を変えるのに使う。
    - ``danger_lines``: 人気帯ごとの消の線（直前の1年で決めたもの）。
    """

    name: str
    test: pd.DataFrame
    history: pd.DataFrame
    races: pd.DataFrame
    history_is_full_year: bool
    danger_lines: dict[str, float]
