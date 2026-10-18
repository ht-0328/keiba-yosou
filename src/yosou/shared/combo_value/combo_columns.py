"""組番（馬番を2桁ずつ並べた文字列）と、馬番の列（``h1``・``h2``・``h3``）を行き来する関数。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 組の馬番の列の名前（1頭目から順）。
HORSE_COLUMNS: tuple[str, ...] = ("h1", "h2", "h3")


def horse_columns(horse_count: int) -> list[str]:
    """組の馬の数ぶんの馬番の列の名前。例: 2 → ``["h1", "h2"]``。"""
    return list(HORSE_COLUMNS[:horse_count])


def split_combo(board: pd.DataFrame, horse_count: int) -> pd.DataFrame:
    """オッズの板（列 ``race_id``・``combo``・``odds``）に、組番を馬番に分けた列（``h1``…）を足す。例: ``0105`` → h1 1・h2 5。"""
    combo = board["combo"].astype(str)
    columns = {name: combo.str[2 * at:2 * at + 2].astype(int) for at, name in enumerate(horse_columns(horse_count))}
    return board.assign(**columns)


def join_combo(frame: pd.DataFrame, horse_count: int) -> pd.Series:
    """馬番の列（``h1``…）を組番の文字列にする。例: h1 1・h2 5 → ``0105``。"""
    parts = [frame[name].astype(int).map("{:02d}".format) for name in horse_columns(horse_count)]
    return pd.Series(np.sum(np.vstack([part.to_numpy(dtype=object) for part in parts]), axis=0), index=frame.index, dtype=object)
