"""組の期待値で選ぶ買い目から、評価できない馬を含む組を外す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.forecast_columns import HORSE_NO, UNRATED

#: レースの表に足す列（そのレースの評価できない馬の馬番か枠番の集まり）。
COLUMN = "unrated_keys"


class UnratedCombos:
    """評価できない馬（列 ``unrated`` が真。``UnratedHorse``）を、組の期待値の買い目（``ComboValuePicker``・``BracketValuePicker``）から外す。

    評価できない馬はモデルの確率がほぼオッズをなぞるだけなので、その馬を含む組の期待値も当てにならない。``attach`` でレースごとに
    評価できない馬の馬番（枠連は枠番）の集まりを足し、``hits`` で組がそれを含むかを見る。印の表に列 ``unrated`` が無ければ（前の形の表）外さない。
    """

    def attach(self, races: pd.DataFrame, marked: pd.DataFrame, frame_of: pd.Series | None = None) -> pd.DataFrame:
        """``races``（1行 = 1レース。列 ``race_id``）に、評価できない馬の馬番の集まり（``frame_of`` を渡せば、(race_id, 馬番) → 枠番 で引いた枠番の集まり）を足す。"""
        if UNRATED not in marked.columns:
            return races.assign(**{COLUMN: [frozenset()] * len(races)})
        unrated = marked[marked[UNRATED].fillna(False).astype(bool)]
        keys: dict[str, set[int]] = {}
        for race_id, horse_no in zip(unrated["race_id"].astype(str), unrated[HORSE_NO].astype(int), strict=True):
            key = horse_no if frame_of is None else frame_of.get((race_id, horse_no))
            if key is not None and pd.notna(key):
                keys.setdefault(race_id, set()).add(int(key))
        return races.assign(**{COLUMN: [frozenset(keys.get(str(race_id), ())) for race_id in races["race_id"]]})

    def hits(self, chosen: pd.DataFrame, names: tuple[str, ...]) -> pd.Series:
        """組（列 ``names`` に馬番か枠番）が、そのレースの評価できない馬を含むか（真偽）。列 ``COLUMN`` が無ければ全部偽。"""
        found = pd.Series(False, index=chosen.index)
        if COLUMN not in chosen.columns or chosen.empty:
            return found
        # 評価できない馬のいるレースはまれなので、そのレースの組だけを見る（印の成績では組が数百万になる）
        some = chosen[chosen[COLUMN].map(len) > 0]
        for name in names:
            hit = np.array([int(key) in keys for key, keys in zip(some[name], some[COLUMN], strict=True)], dtype=bool)
            found.loc[some.index] = found.loc[some.index].to_numpy() | hit
        return found
