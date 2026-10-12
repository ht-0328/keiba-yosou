"""馬ごとの表から、レースごとの確定着順と確定の人気を読む。"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from yosou.shared.dataset import HORSE_NO, RACE_ID

from .horse_frame import FINISH, POPULARITY


class FinishLoader:
    """馬ごとの表（研究「既存モデルの改善」の ``tables/<表の名前>/``）の ID と評価用の列だけを読み、レースID → 馬番 → 確定着順（か確定の人気）にする。

    特徴量の表（大きい）は読まない。着順の付かない馬（取消・中止）は着順に入れない。
    """

    def __init__(self, tables: Path, table: str) -> None:
        folder = Path(tables) / table
        ids = pd.read_pickle(folder / "ids.pkl")[[RACE_ID, HORSE_NO]]
        evaluation = pd.read_pickle(folder / "evaluation.pkl")[[FINISH, POPULARITY]]
        numbers = {column: pd.to_numeric(evaluation[column], errors="coerce") for column in (FINISH, POPULARITY)}
        self._frame = ids.assign(**numbers, **{HORSE_NO: pd.to_numeric(ids[HORSE_NO], errors="coerce")}).dropna(subset=[HORSE_NO])

    def finishes(self, race_ids: Iterable[str]) -> dict[str, dict[int, int]]:
        """レースID → 馬番 → 確定着順。"""
        return self._by_race(race_ids, FINISH)

    def popularity(self, race_ids: Iterable[str]) -> dict[str, dict[int, int]]:
        """レースID → 馬番 → 確定の単勝人気。"""
        return self._by_race(race_ids, POPULARITY)

    def _by_race(self, race_ids: Iterable[str], column: str) -> dict[str, dict[int, int]]:
        wanted = self._frame[self._frame[RACE_ID].isin(set(race_ids)) & self._frame[column].notna()]
        return {race_id: dict(zip(rows[HORSE_NO].astype(int), rows[column].astype(int)))
                for race_id, rows in wanted.groupby(RACE_ID)}
