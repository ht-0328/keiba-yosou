"""型の中の組から、期待値の線とトリガミで買う組を決める。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 組の表の列（期待値・オッズ）。
VALUE, ODDS = "value", "odds"


class TicketPicker:
    """型に入る組（``FormationMask`` が真の行）から、1レースごとに買う組を決める（docs/01 の 2・4）。

    1. 期待値の線 ``value_line`` があれば、期待値が線以上の組だけ残す。残る組が無いレースは、型の中で期待値がいちばん高い組を1点残す
       （全レースを買うため。期待値が無い組だけのレースは、オッズがいちばん高い組）。
    2. 1レースの点数が ``max_points`` を超えるレースは、期待値の高い順に ``max_points`` 点まで残す（利用者の決定「1レース 1万円」）。
    3. オッズの無い組（無投票・取消）は外す。
    4. トリガミを外す（道具「印の成績」の ``TorigamiFilter`` と同じ決まり）: 1レースの点数を p として、オッズの低い順に、
       「オッズ ≤ 残りの点数」の組を順に外す（最初に「オッズ > 残りの点数」になった組から上は残す）。
    戻り値は、``combos`` と同じ長さの真偽（買う組）。
    """

    def pick(self, combos: pd.DataFrame, in_formation: np.ndarray, value_line: float | None, max_points: int | None = None) -> np.ndarray:
        rows = combos.loc[in_formation, ["race_id", VALUE, ODDS]]
        if rows.empty:
            return np.zeros(len(combos), dtype=bool)
        chosen = pd.Series(True, index=rows.index)
        if value_line is not None:
            chosen = rows[VALUE] >= value_line
            races_without = ~chosen.groupby(rows["race_id"]).transform("any")
            if races_without.any():
                fallback = rows[races_without].copy()
                score = fallback[VALUE].fillna(-np.inf) + fallback[ODDS].fillna(0.0) * 1e-9
                best = score.groupby(fallback["race_id"]).idxmax()
                chosen.loc[best.to_numpy()] = True
        chosen &= rows[ODDS].notna()
        if max_points is not None:
            kept = rows[chosen]
            score = kept[VALUE].fillna(-np.inf) + kept[ODDS].fillna(0.0) * 1e-9
            order = score.groupby(kept["race_id"]).rank(method="first", ascending=False)
            chosen = chosen & (order.reindex(rows.index) <= max_points).fillna(False)
        kept = rows[chosen]
        if kept.empty:
            return np.zeros(len(combos), dtype=bool)
        torigami = self._torigami(kept)
        result = np.zeros(len(combos), dtype=bool)
        result[combos.index.get_indexer(kept.index[~torigami])] = True
        return result

    @staticmethod
    def _torigami(kept: pd.DataFrame) -> np.ndarray:
        """``kept`` の各行がトリガミで外れるか（``kept`` の並び順）。"""
        ordered = kept.sort_values(["race_id", ODDS], kind="stable")
        points = ordered.groupby("race_id")[ODDS].transform("size").to_numpy()
        rank = ordered.groupby("race_id").cumcount().to_numpy()
        remaining = points - rank
        keeps = ordered[ODDS].to_numpy() > remaining
        first_keep = pd.Series(keeps, index=ordered.index).groupby(ordered["race_id"].to_numpy()).cummax().to_numpy()
        dropped = pd.Series(~first_keep, index=ordered.index)
        return dropped.reindex(kept.index).to_numpy()
