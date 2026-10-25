"""セルごとに、選ぶ期間の成績で型の候補を1つ選ぶ。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from .day_table import HIT_RACES, PAYOUT, POINTS, RACES
from .formation import MAX_POINTS, TOKEN_POINTS, Formation
from .recovery_bootstrap import RecoveryBootstrap

#: 当たったレースの下限（これ以上の候補の中から選ぶ）。
MIN_HITS = 30
#: 1点の額（円）。
POINT_YEN = 100.0
#: セルごとに候補を限る決まり（セル, 型 → 候補に入れるか）。
Allowed = Callable[[str, Formation], bool]


@dataclass(frozen=True)
class CellChoice:
    """1つのセルで選んだ候補。``index`` は候補の位置、``lower`` は回収率の 90% の幅の下の端、``recovery`` は回収率、``hits`` は当たったレース、
    ``races`` は買ったレース、``points_per_race`` は1レースの平均の点数、``enough`` は当たりが ``MIN_HITS`` 以上の候補から選べたか、
    ``token`` は最小の額（1点）に落としたセルか（2回目の決まり。成績は落とす前の型のもの）、``skip`` はこの券種を買わないセルか（3回目の決まり）。"""

    cell: str
    index: int
    label: str
    recovery: float
    lower: float
    hits: int
    races: int
    points_per_race: float
    enough: bool
    token: bool = False
    skip: bool = False


class CellSelector:
    """候補ごとのセル × 開催日の集計（配列 [候補, セル, 開催日, 4]）から、選ぶ期間の開催日（``day_mask``）だけで、セルごとに
    「当たったレースが ``MIN_HITS`` 以上の候補のうち、回収率の 90% の幅の下の端がいちばん高い」候補を選ぶ（docs/01 の 5）。
    当たりが足りる候補が無いセルは、全候補の中で下の端がいちばん高いもの。``table()`` は候補 × セルの成績の表（1券種）。

    ``formations`` を渡すと、上限 12点の型だけから選ぶ。``token`` が真なら（2回目。docs/01 の 7）、選んだ型の下の端が 100% に届かないセルは
    同じ型の上限 1点の候補に置き換える（最小の額で買って全レースを買う形を守る）。
    ``allowed`` を渡すと（3回目。docs/01 の 8）、セルごとに候補をその決まりに合う型だけに限る。``skip_cells`` のセルは、この券種を買わない（``skip``）。
    """

    def __init__(self, labels: list[str], cells: list[str], min_hits: int = MIN_HITS, formations: Sequence[Formation] | None = None,
                 token: bool = False, allowed: Allowed | None = None, skip_cells: Sequence[str] = ()) -> None:
        self._labels = list(labels)
        self._cells = list(cells)
        self._min_hits = min_hits
        self._formations = list(formations) if formations is not None else None
        if self._formations is not None and [formation.label for formation in self._formations] != self._labels:
            raise ValueError("候補の名前の並びが、保存した集計と合っていません")
        if (token or allowed is not None) and self._formations is None:
            raise ValueError("1点に落とす決まりや候補を限る決まりには、型の並び（formations）が要る")
        self._token = token
        self._allowed = allowed
        self._skip_cells = set(skip_cells)

    def select(self, values: np.ndarray, day_mask: np.ndarray) -> list[CellChoice]:
        picked = values[:, :, day_mask]                       # [候補, セル, 日, 4]
        bootstrap = RecoveryBootstrap(int(day_mask.sum()))
        choices = []
        for cell_index, cell in enumerate(self._cells):
            full = self._candidates(cell)
            stakes = picked[:, cell_index, :, POINTS] * POINT_YEN
            payouts = picked[:, cell_index, :, PAYOUT]
            lower = bootstrap.lower(stakes, payouts)
            hits = picked[:, cell_index, :, HIT_RACES].sum(axis=1)
            races = picked[:, cell_index, :, RACES].sum(axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                recovery = np.where(stakes.sum(axis=1) > 0, payouts.sum(axis=1) / stakes.sum(axis=1), np.nan)
            enough = hits >= self._min_hits
            pool = np.where(enough & full, lower, np.nan)
            if not np.isfinite(pool).any():
                pool = np.where(full, lower, np.nan)
            index = int(np.nanargmax(pool)) if np.isfinite(pool).any() else int(np.flatnonzero(full)[0])
            points = picked[index, cell_index, :, POINTS].sum() / races[index] if races[index] > 0 else float("nan")
            choice = CellChoice(cell, index, self._labels[index], float(recovery[index]), float(lower[index]), int(hits[index]),
                                int(races[index]), float(points), bool(enough[index]), skip=cell in self._skip_cells)
            if self._token and not choice.skip and not (choice.lower >= 1.0):
                choice = self._to_token(choice)
            choices.append(choice)
        return choices

    def _candidates(self, cell: str) -> np.ndarray:
        """そのセルで候補に入れる型（上限 12点の型のうち、``allowed`` に合うもの）。型の並びが無ければ全部。"""
        if self._formations is None:
            return np.ones(len(self._labels), dtype=bool)
        full = np.array([formation.max_points == MAX_POINTS for formation in self._formations])
        if self._allowed is None:
            return full
        permitted = np.array([self._allowed(cell, formation) for formation in self._formations])
        return full & permitted if (full & permitted).any() else full

    def _to_token(self, choice: CellChoice) -> CellChoice:
        """同じ型の上限 1点の候補に置き換える（成績の値は落とす前の型のまま）。"""
        token = replace(self._formations[choice.index], max_points=TOKEN_POINTS)
        index = self._labels.index(token.label)
        return replace(choice, index=index, label=token.label, token=True)

    def table(self, values: np.ndarray, day_mask: np.ndarray) -> pd.DataFrame:
        """候補 × セルの成績（回収率・下の端・当たり・レース・1レースの点数）。選ぶときの根拠を残すための表。"""
        picked = values[:, :, day_mask]
        bootstrap = RecoveryBootstrap(int(day_mask.sum()))
        rows = []
        for cell_index, cell in enumerate(self._cells):
            stakes = picked[:, cell_index, :, POINTS] * POINT_YEN
            payouts = picked[:, cell_index, :, PAYOUT]
            lower = bootstrap.lower(stakes, payouts)
            for index, label in enumerate(self._labels):
                stake = stakes[index].sum()
                races = picked[index, cell_index, :, RACES].sum()
                rows.append({"セル": cell, "型": label, "回収率": payouts[index].sum() / stake if stake > 0 else np.nan, "下の端": lower[index],
                             "当たったレース": int(picked[index, cell_index, :, HIT_RACES].sum()), "レース": int(races),
                             "1レースの点数": picked[index, cell_index, :, POINTS].sum() / races if races > 0 else np.nan})
        return pd.DataFrame(rows)
