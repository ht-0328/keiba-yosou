"""Top3Positions（3着以内の馬の4コーナーの位置を数える）のテスト。出走は架空。"""

from __future__ import annotations

import pandas as pd

from 発走前の通知.position_counts import PositionCounts
from 発走前の通知.top3_positions import Top3Positions


def _race(race_id: str, finishes: dict[int, int], corners: list[float]) -> pd.DataFrame:
    """``corners`` は各馬の4コーナーの順位、``finishes`` は 4コーナーの順位 → 着順（それ以外の馬は4着以下）。"""
    return pd.DataFrame({"race_id": race_id, "corner": corners,
                         "finish": [finishes.get(int(corner), 9) if pd.notna(corner) else None for corner in corners]})


def test_12頭立てを3つに分けて_3着以内の馬の位置を数える() -> None:
    # 4コーナー 1番手が1着（前）、5番手が2着（4/11 = 0.36 で中）、9番手が3着（8/11 = 0.73 で後ろ）
    runs = _race("A", {1: 1, 5: 2, 9: 3}, list(range(1, 13)))
    assert Top3Positions().count(runs) == PositionCounts(races=1, top3=3, front=1, middle=1, back=1)


def test_まだ終わっていないレースと_コーナーの順位の無いレースは数えない() -> None:
    finished = _race("A", {1: 1, 2: 2, 4: 3}, list(range(1, 13)))   # 4番手は 3/11 = 0.27 で前
    unfinished = pd.DataFrame({"race_id": "B", "corner": [1.0, 2.0], "finish": [None, None]})
    straight = pd.DataFrame({"race_id": "C", "corner": [None, None], "finish": [1, 2]})
    counts = Top3Positions().count(pd.concat([finished, unfinished, straight], ignore_index=True))
    assert counts == PositionCounts(races=1, top3=3, front=3, middle=0, back=0)
    assert counts.front_share == 1.0 and counts.back_share == 0.0


def test_何も無ければ0() -> None:
    empty = pd.DataFrame({"race_id": [], "corner": [], "finish": []})
    assert Top3Positions().count(empty) == PositionCounts(0, 0, 0, 0, 0)
