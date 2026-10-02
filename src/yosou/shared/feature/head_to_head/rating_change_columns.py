"""レーティングの履歴から、前走と近5走でどれだけ動いたかの列を作る。"""

from __future__ import annotations

import pandas as pd

from .head_to_head_columns import LAST_CHANGE, RATING, RECENT_CHANGE, RECENT_RUNS


class RatingChangeColumns:
    """``RatingHistoryBuilder`` の履歴から、馬ごとの「前走での変化」と「近5走の変化」を作る。

    履歴の値は「そのレースの前日までのレーティング」なので、1つ前の走の値との差が、前走の結果で動いた幅になる。
    近5走の変化は、5つ前の走の値との差（5走に満たなければ、初めて走ったときの値との差）。初めて走る馬はどちらも欠損値。
    列は ``対戦レーティングの前走での変化``・``対戦レーティングの近5走の変化``。行の並びと index は ``history`` と同じ。
    """

    def build(self, history: pd.DataFrame) -> pd.DataFrame:
        ordered = history.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        by_horse = ordered.groupby("horse_id", sort=False)[RATING]
        rating = ordered[RATING]
        earlier_runs = by_horse.cumcount()
        recent_base = by_horse.shift(RECENT_RUNS).fillna(by_horse.transform("first"))
        changes = pd.DataFrame({
            LAST_CHANGE: rating - by_horse.shift(1),
            RECENT_CHANGE: (rating - recent_base).where(earlier_runs > 0),
        }, index=ordered.index)
        return changes.loc[history.index]
