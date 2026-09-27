"""券種どうしの値段の食い違いを、帯ごとの成績と、食い違いの大きいレースの一覧にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 比（3連単から見た確率 ÷ その券種自身から見た確率）の帯。
RATIO_BANDS: tuple[float, ...] = (0.0, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0, np.inf)
#: 事例に出す組の、3連単から見た確率の下限。極端な人気薄の組は、比が大きくても当たりが見込めない。
MIN_CASE_PROBABILITY = 0.02


class GapCases:
    """券種自身から見た組の確率（``own``）と、3連単から見た組の確率（``derived``）を並べた表を読む。

    入力の列: rid・flat・odds・price・own・derived・payout（100円あたり）。
    - ``by_band``: 比の帯ごとの、点数・当たり・見込みの当たり（3連単から見た確率の合計）・全部買ったときの回収率。
    - ``by_band_and_odds``: 同じものを、オッズの帯でも分けたもの。
    - ``top_cases``: 比がいちばん大きい組を、レースごとに1つ選び、比の大きい順に並べた一覧。
    """

    def __init__(self, rows: pd.DataFrame) -> None:
        self._rows = rows.assign(ratio=rows["derived"] / rows["own"].replace(0, np.nan))

    def by_band(self) -> pd.DataFrame:
        return self._summarize(self._rows.groupby(self._band(), observed=True))

    def by_band_and_odds(self, odds_bands: tuple[float, ...]) -> pd.DataFrame:
        odds_band = pd.cut(self._rows["odds"], odds_bands)
        return self._summarize(self._rows.groupby([odds_band, self._band()], observed=True))

    def top_cases(self, count: int) -> pd.DataFrame:
        pool = self._rows[self._rows["derived"] >= MIN_CASE_PROBABILITY]
        best = pool.sort_values("ratio", ascending=False).drop_duplicates("rid")
        return best.head(count).reset_index(drop=True)

    def _band(self) -> pd.Series:
        return pd.cut(self._rows["ratio"], RATIO_BANDS, right=False).rename("比の帯")

    def _summarize(self, grouped) -> pd.DataFrame:
        summary = grouped.agg(点数=("payout", "size"), 当たり=("payout", lambda p: int((p > 0).sum())),
                              見込みの当たり=("derived", "sum"), 払戻=("payout", "sum"))
        summary["回収率"] = (summary["払戻"] / (summary["点数"] * 100) * 100).round(1)
        summary["見込みの当たり"] = summary["見込みの当たり"].round(1)
        return summary.drop(columns="払戻").reset_index()
