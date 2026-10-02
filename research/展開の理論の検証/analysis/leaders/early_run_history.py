"""各出走に、今回より前の走での序盤の位置取りをまとめた列を足す。"""

from __future__ import annotations

import pandas as pd

#: 出力の列の名前。
RUNS_BEFORE = "過去走の数"
LEAD_RATE = "先頭率（近5走）"
LEAD_RATE_SAME_SURFACE = "先頭率（同じ芝ダの近5走）"
LED_RECENTLY = "近3走で逃げた回数"
POSITION_MEAN = "序盤の位置の平均（近5走）"
#: まとめる走の数。
_RECENT, _SHORT = 5, 3


class EarlyRunHistory:
    """出走の表（1行 = 1頭。DB にある 2011年からの中央・平地の全出走）に、今回より前の走だけから作った列を足す。

    - 先頭率: 最初のコーナーを先頭で回った割合。例: 近5走で2回なら 0.4。最初のコーナーの記録が無い走（直線コースなど）は数えない。
    - 同じ芝ダの先頭率: 今回と同じ芝・ダートの走だけで数えた先頭率。
    - 近3走で逃げた回数: JV-Data の脚質判定が逃げだった回数。
    - 序盤の位置の平均: 最初のコーナーの位置（0 が先頭、1 が最後方）の平均。
    どれも今回の走は含まない。過去走が無ければ欠損値（逃げた回数は 0）。
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        ordered = runners.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        rank = ordered["first_corner_rank"].astype("Float64")
        lead = (rank == 1).astype("Float64").where(rank.notna())
        position = (rank - 1) / (ordered["field_size"] - 1).where(ordered["field_size"] > 1)
        led = (ordered["style"] == "逃げ").astype(float)
        by_horse = ordered["horse_id"]
        by_surface = [ordered["horse_id"], ordered["surface"]]
        columns = {
            RUNS_BEFORE: ordered.groupby("horse_id").cumcount(),
            LEAD_RATE: self._recent_mean(lead, by_horse, _RECENT),
            LEAD_RATE_SAME_SURFACE: self._recent_mean(lead, by_surface, _RECENT),
            LED_RECENTLY: self._recent_sum(led, by_horse, _SHORT),
            POSITION_MEAN: self._recent_mean(position, by_horse, _RECENT),
        }
        return runners.join(pd.DataFrame(columns, index=ordered.index))

    def _recent_mean(self, values: pd.Series, keys, window: int) -> pd.Series:
        previous = values.astype(float).groupby(keys).shift()
        rolled = previous.groupby(keys).rolling(window, min_periods=1).mean()
        return rolled.reset_index(level=list(range(rolled.index.nlevels - 1)), drop=True)

    def _recent_sum(self, values: pd.Series, keys, window: int) -> pd.Series:
        previous = values.groupby(keys).shift()
        rolled = previous.groupby(keys).rolling(window, min_periods=1).sum()
        return rolled.reset_index(level=list(range(rolled.index.nlevels - 1)), drop=True).fillna(0.0)
