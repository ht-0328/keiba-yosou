"""展開の予想①②③の予測から、脚質の確率とペースの確率を出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature.pace_forecast import pace_forecast_columns as source

from . import names


class StyleProbabilities:
    """元の予測の表（1行 = 1頭。``pace_forecast.SOURCE_COLUMNS`` の ``p_leader``・``p_front``・``p_middle``・``p_back``・
    ``p_slow``・``p_high``）から、各馬が逃げ・先行・差し・追込の位置を取る確率と、レースのペースの確率を出す（設計書 05 の 2）。

    - 逃げ = ① 先頭になる確率。先行 = ② 先団の確率 − 逃げ（先団は前から3分の1までで、先頭を含むため。負なら 0）。
      差し = ② 中団の確率。追込 = ② 後方の確率。4つの合計が 1 になるようにそろえる。
    - スロー・ハイ = ③ の確率。平均 = 1 − スロー − ハイ（負なら 0）。3つの合計が 1 になるようにそろえる。
    予測の無い行は欠損値。
    """

    def of(self, forecasts: pd.DataFrame) -> pd.DataFrame:
        """列は ``names.STYLES`` と ``names.PACES``。index は ``forecasts`` と同じ。"""
        leader = forecasts[source.LEADER].astype("float64")
        styles = pd.DataFrame({
            names.LEAD: leader,
            names.FRONT: (forecasts[source.FRONT].astype("float64") - leader).clip(lower=0.0),
            names.MIDDLE: forecasts[source.MIDDLE].astype("float64"),
            names.BACK: forecasts[source.BACK].astype("float64"),
        })
        slow, high = forecasts[source.SLOW].astype("float64"), forecasts[source.HIGH].astype("float64")
        paces = pd.DataFrame({names.SLOW: slow, names.EVEN: (1.0 - slow - high).clip(lower=0.0), names.HIGH: high})
        return pd.concat([self._normalized(styles), self._normalized(paces)], axis=1)

    def _normalized(self, table: pd.DataFrame) -> pd.DataFrame:
        total = table.sum(axis=1, skipna=False)
        return table.div(total.where(total > 0), axis=0)
