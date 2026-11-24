"""組の馬の材料をまとめた材料。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .combo_members import ComboMembers
from .longshot_rule import is_backed_longshot
from .material_names import DG, E3, FLOOR, P3, PM, POP, R3, RPM, RW

NAMES: tuple[str, ...] = (
    "s_e3", "min_e3", "max_e3", "s_r3", "s_rw", "s_rpm", "s_pop", "max_pop", "min_pop", "n_ls_in", "n_dg_in", "s_lp3", "s_lpm", "log_ratio",
)
#: 組の中でいちばん人気のある馬の単勝人気（``RaceFeatures`` が「1番人気を含まない組か」を見るのに使う）。
MIN_POPULARITY = "min_pop"


class ComboSummaryFeatures:
    """組の馬（2頭か3頭）の材料の、和・最小・最大・数を材料にする。

    - ``s_e3``・``min_e3``・``max_e3``: 予想と複勝の市場の差（e3）の和・最小・最大。
    - ``s_r3``・``s_rw``・``s_rpm``: 予想 ÷ 市場の比の対数（r3・rw・rpm）の和。
    - ``s_pop``・``max_pop``・``min_pop``: 単勝人気の和・最大・最小。例: 2番人気と7番人気の組は 9・7・2。
    - ``n_ls_in``: 組の中の「予想が買っている穴馬」（6番人気以下で e3 が 0.05 以上）の数。``n_dg_in``: 危険な人気馬の数。
    - ``s_lp3``・``s_lpm``: 予想の3着以内の確率と、複勝オッズから見た3着以内率の、対数の和。
    - ``log_ratio``: 馬単・3連単は 1頭目の rw ＋ 2頭目以降の r3 の和。順不同の券種は ``s_r3`` と同じ。
    """

    def of(self, members: ComboMembers, index: pd.Index) -> pd.DataFrame:
        """行の並びは ``members`` と同じ。``index`` は付ける index。"""
        edge, top3_ratio, popularity = members.in_feature_order(E3), members.in_feature_order(R3), members.in_feature_order(POP)
        return pd.DataFrame({
            "s_e3": edge.sum(axis=1), "min_e3": edge.min(axis=1), "max_e3": edge.max(axis=1),
            "s_r3": top3_ratio.sum(axis=1), "s_rw": members.in_feature_order(RW).sum(axis=1),
            "s_rpm": members.in_feature_order(RPM).sum(axis=1),
            "s_pop": popularity.sum(axis=1), "max_pop": popularity.max(axis=1), MIN_POPULARITY: popularity.min(axis=1),
            "n_ls_in": is_backed_longshot(popularity, edge).sum(axis=1), "n_dg_in": members.in_feature_order(DG).sum(axis=1),
            "s_lp3": self._log_sum(members.in_feature_order(P3)), "s_lpm": self._log_sum(members.in_feature_order(PM)),
            "log_ratio": self._log_ratio(members, top3_ratio),
        }, index=index)

    def _log_sum(self, probabilities: np.ndarray) -> np.ndarray:
        return np.log(np.clip(probabilities, FLOOR, None)).sum(axis=1)

    def _log_ratio(self, members: ComboMembers, top3_ratio: np.ndarray) -> np.ndarray:
        if not members.is_ordered:
            return top3_ratio.sum(axis=1)
        return members.in_feature_order(RW)[:, 0] + top3_ratio[:, 1:].sum(axis=1)
