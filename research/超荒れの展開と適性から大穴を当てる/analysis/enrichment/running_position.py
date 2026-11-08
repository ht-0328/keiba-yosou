"""その走で実際に取った位置（結果側）と、レース前に見込まれた位置・枠の側の列を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: 脚質の区切り（前から3分の1まで・3分の2まで。展開スコアの脚質の決め方と同じ）。
FRONT_LIMIT, MIDDLE_LIMIT = 1 / 3, 2 / 3
#: 見込みの位置を作る近走の数（展開スコアの脚質の決め方と同じ5走）。
RECENT_RUNS = 5
#: 「いつもより前・後ろ」とみなす、見込みとの差（0〜1 の位置で）。
SHIFT_LIMIT = 0.25
STYLES: tuple[str, ...] = ("逃げ", "先行", "差し", "追込")


@dataclass(frozen=True)
class RunningPosition:
    """出走の表（全部の過去走を含む。``first_corner_rank``・``corner4``・``field_size``・``horse_no`` が要る）に足す列:

    - ``early_position``: 最初のコーナーの位置（0 が先頭、1 が最後方）。結果側
    - ``result_style``: その走の脚質（最初のコーナーで先頭 = 逃げ、3分の1まで先行、3分の2まで差し、残り追込）。結果側
    - ``front_or_back``: 結果の脚質を 前（逃げ・先行）か 後ろ（差し・追込）にまとめたもの。結果側
    - ``corner4_group``: 4コーナーの位置を 前・中・後ろ に3つに分けたもの。結果側
    - ``expected_position``: 今回より前の近5走の、最初のコーナーの位置の平均（レース前に分かる）
    - ``position_shift``: 今回の位置が見込みより 0.25 以上前なら「いつもより前」、後ろなら「いつもより後ろ」、ほかは「いつもどおり」
    - ``horse_side``: 馬番が頭数の内3分の1なら 内、外3分の1なら 外、ほかは 中（レース前に分かる）
    """

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.sort_values(["horse_id", "race_date", "race_id"], kind="stable").reset_index(drop=True)
        size = frame["field_size"].where(frame["field_size"] > 1)
        early = (frame["first_corner_rank"] - 1) / (size - 1)
        frame["early_position"] = early
        frame["result_style"] = self._style(frame["first_corner_rank"], early)
        frame["front_or_back"] = frame["result_style"].map({"逃げ": "前", "先行": "前", "差し": "後ろ", "追込": "後ろ"})
        corner4 = (frame["corner4"] - 1) / (size - 1)
        frame["corner4_group"] = self._thirds(corner4, ("前", "中", "後ろ"))
        previous = early.groupby(frame["horse_id"], sort=False).shift()
        rolled = previous.groupby(frame["horse_id"], sort=False).rolling(RECENT_RUNS, min_periods=1).mean()
        frame["expected_position"] = rolled.reset_index(level=0, drop=True).sort_index()
        frame["position_shift"] = self._shift(early - frame["expected_position"])
        side = frame["horse_no"] / frame["field_size"]
        frame["horse_side"] = np.select([side <= FRONT_LIMIT, side > MIDDLE_LIMIT], ["内", "外"], default="中")
        return frame

    @staticmethod
    def _style(rank: pd.Series, early: pd.Series) -> pd.Series:
        known = early.notna().to_numpy()
        conditions = [known & (rank == 1).to_numpy(), known & (early <= FRONT_LIMIT).to_numpy(),
                      known & (early <= MIDDLE_LIMIT).to_numpy(), known]
        return pd.Series(np.select(conditions, list(STYLES), default=None), index=rank.index, dtype="object")

    @staticmethod
    def _thirds(position: pd.Series, labels: tuple[str, str, str]) -> pd.Series:
        known = position.notna().to_numpy()
        conditions = [known & (position <= FRONT_LIMIT).to_numpy(), known & (position <= MIDDLE_LIMIT).to_numpy(), known]
        return pd.Series(np.select(conditions, list(labels), default=None), index=position.index, dtype="object")

    @staticmethod
    def _shift(difference: pd.Series) -> pd.Series:
        known = difference.notna().to_numpy()
        conditions = [known & (difference <= -SHIFT_LIMIT).to_numpy(), known & (difference >= SHIFT_LIMIT).to_numpy(), known]
        labels = ["いつもより前", "いつもより後ろ", "いつもどおり"]
        return pd.Series(np.select(conditions, labels, default=None), index=difference.index, dtype="object")
