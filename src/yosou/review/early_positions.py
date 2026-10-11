"""出走ごとの、実際の序盤の位置と、レース前に見込まれた序盤の位置。"""

from __future__ import annotations

import pandas as pd

from yosou.development_score.pre_race_style import RECENT_RUNS
from yosou.shared.feature import as_numbers


class EarlyPositions:
    """序盤の位置は、最初のコーナーの順位を頭数で 0〜1 にしたもの（0 が先頭、1 が最後方）。

    - 実際の序盤の位置: その走の最初のコーナーの順位から
    - 見込みの序盤の位置: その馬の今回より前の近5走の序盤の位置の平均（展開スコアの脚質の決め方と同じ元。レース前に分かる）

    最初のコーナーの記録が無い走（直線コースなど）や過去走の無い馬は欠損値。「出遅れ」は、実際の位置が見込みより 0.4 以上後ろだったこと。
    """

    def of(self, runs: pd.DataFrame) -> pd.DataFrame:
        """列は ``actual``・``expected``。行の並びと index は ``runs`` と同じ。"""
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        rank, field_size = as_numbers(ordered["first_corner_rank"]), as_numbers(ordered["field_size"])
        actual = ((rank - 1) / (field_size - 1)).where(field_size > 1)
        previous = actual.groupby(ordered["horse_id"]).shift()
        rolled = previous.groupby(ordered["horse_id"]).rolling(RECENT_RUNS, min_periods=1).mean().reset_index(level=0, drop=True)
        return pd.DataFrame({"actual": actual, "expected": rolled.reindex(ordered.index)}, index=ordered.index).reindex(runs.index)
