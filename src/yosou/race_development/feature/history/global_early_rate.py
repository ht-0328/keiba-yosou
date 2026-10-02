"""全体の先頭率・先団率。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers

#: 数える日数（前日までの 365日）。
_WINDOW = "365D"
#: 数えられないとき（記録が無い期間）の割合。出走頭数の平均から見込んだ値（設計書 09 の K）。
DEFAULT_LEAD_RATE, DEFAULT_FRONT_RATE = 0.07, 0.33


class GlobalEarlyRate:
    """開催日ごとに、前日までの 365日の全出走のうち、最初のコーナーで先頭・先団だった割合を出す（設計書 09 の K の「平滑化」）。

    レースの記録（``race_history``。1行 = 1レース）から数える。1レースの先頭は1頭（先頭が決まったレースだけ）、
    先団は ``1 + (頭数 − 1) ÷ 3`` の切り捨て頭数、出走は頭数とみなす。同じ日のレースは数えない。
    """

    def of(self, days: pd.Series, race_history: pd.DataFrame) -> pd.DataFrame:
        """``days`` は出走の行ごとの開催日。列 ``lead``・``front``、行の並びと index は ``days`` と同じ。"""
        daily = self._daily_counts(race_history)
        rolled = daily.rolling(_WINDOW, closed="left").sum()
        rates = pd.DataFrame({"lead": rolled["leads"] / rolled["starts"], "front": rolled["fronts"] / rolled["starts"]})
        found = rates.reindex(pd.to_datetime(days).to_numpy())
        return pd.DataFrame({
            "lead": found["lead"].fillna(DEFAULT_LEAD_RATE).to_numpy(),
            "front": found["front"].fillna(DEFAULT_FRONT_RATE).to_numpy(),
        }, index=days.index)

    def _daily_counts(self, race_history: pd.DataFrame) -> pd.DataFrame:
        """日ごとの出走・先頭・先団の数（毎日の行があり、レースの無い日は 0）。"""
        if race_history.empty:
            return pd.DataFrame({"starts": [], "leads": [], "fronts": []}, index=pd.DatetimeIndex([]))
        field = as_numbers(race_history["field_size"])
        valid = race_history["first_corner_no"].notna() & ~race_history["corner_laps_over_one"].astype(bool)
        valid &= race_history["finished"].astype(bool) & (field > 1)
        counts = pd.DataFrame({
            "starts": field.where(valid, 0.0),
            "leads": race_history["first_corner_leader_no"].notna().astype("float64").where(valid, 0.0),
            "fronts": np.floor(1 + (field - 1) / 3).where(valid, 0.0),
        })
        daily = counts.groupby(pd.to_datetime(race_history["race_date"]).to_numpy()).sum()
        return daily.asfreq("D", fill_value=0.0)
