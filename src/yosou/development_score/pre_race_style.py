"""出走ごとに、レース前に分かる脚質を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers

from . import names

#: 先頭率がこの値以上なら「逃げ」（研究「展開の理論の検証」で決めた逃げたい馬の線）。
LEAD_LINE = 0.4
#: 先頭率と序盤の位置の平均を数える、今回より前の走の数。
RECENT_RUNS = 5
#: 序盤の位置（0 が先頭、1 が最後方）の区切り。先行は前から3分の1まで、差しは3分の2まで（展開の予想の設計書 10 の 3 と同じ）。
FRONT_LIMIT, MIDDLE_LIMIT = 1 / 3, 2 / 3


class PreRaceStyle:
    """出走の表（1行 = 1頭。``horse_id``・``race_date``・``race_id``・``first_corner_rank``・``field_size``）に、
    今回より前の近5走だけから決めた脚質を付ける。

    - 先頭率: 最初のコーナーを先頭で回った割合。0.4 以上なら「逃げ」。
    - それ以外は、序盤の位置（最初のコーナーの順位を頭数で 0〜1 にしたもの）の平均で、3分の1までなら「先行」、
      3分の2までなら「差し」、それより後ろなら「追込」。
    最初のコーナーの記録が無い走（直線コースなど）は数えない。過去走が無い馬（新馬など）は欠損値。
    結果の脚質（JV-Data の脚質判定）で分けると「その日に前に行けた馬はもともと調子が良かった」分が混ざるので使わない
    （設計書 05 の 2）。例: 近5走で先頭 2回なら先頭率 0.4 で「逃げ」。
    """

    def of(self, runs: pd.DataFrame) -> pd.Series:
        """行ごとの脚質（``names.STYLES`` のどれか、または欠損値）。index は ``runs`` と同じ。"""
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        rank, field_size = as_numbers(ordered["first_corner_rank"]), as_numbers(ordered["field_size"])
        position = ((rank - 1) / (field_size - 1)).where(field_size > 1)
        lead = (rank == 1).astype("float64").where(rank.notna())
        horse = ordered["horse_id"]
        lead_rate, position_mean = self._recent_mean(lead, horse), self._recent_mean(position, horse)
        style = np.select(
            [lead_rate >= LEAD_LINE, position_mean <= FRONT_LIMIT, position_mean <= MIDDLE_LIMIT, position_mean > MIDDLE_LIMIT],
            list(names.STYLES), default=None,
        )
        return pd.Series(style, index=ordered.index, dtype="object").reindex(runs.index)

    def _recent_mean(self, values: pd.Series, horse: pd.Series) -> pd.Series:
        """馬ごとに、今回を除く直近 ``RECENT_RUNS`` 走の平均（記録の無い走は数えない。1走も無ければ欠損値）。"""
        previous = values.groupby(horse).shift()
        rolled = previous.groupby(horse).rolling(RECENT_RUNS, min_periods=1).mean()
        return rolled.reset_index(level=0, drop=True).reindex(values.index)
