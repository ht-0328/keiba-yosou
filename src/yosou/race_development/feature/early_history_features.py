"""K. 序盤の位置取りの履歴（15個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import EntryRecords

from .history import DailyRate, EarlyRunSummary, GlobalEarlyRate

#: 騎手の先頭率・先団率を出すのに要る、前日までの 365日の騎乗の数（少ない数の割合は当てにならないため）。
JOCKEY_MIN_RIDES = 20


class EarlyHistoryFeatures:
    """K. この馬が、これまで序盤にどこを走ってきたか（設計書 09 の K）。``FeatureGroup`` を守る。

    馬の13個は過去走から（``EarlyRunSummary``）、騎手の2個は騎手の日ごとの数から（``DailyRate``）作る。
    先頭率・先団率を寄せる先の全体の割合は、レースの記録（``race_history``）から数える（``GlobalEarlyRate``）。
    """

    def __init__(self) -> None:
        self._summary = EarlyRunSummary()
        self._global_rate = GlobalEarlyRate()

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        prior = self._global_rate.of(entries["race_date"], records.race_history)
        summary = self._summary.build(entries, records.past_runs, prior)
        jockey = DailyRate(entries, "jockey_code", JOCKEY_MIN_RIDES)
        return summary.assign(**{
            "騎手の先頭率": jockey.of(records.jockey_days, "early_leads", "early_starts"),
            "騎手の先団率": jockey.of(records.jockey_days, "early_fronts", "early_starts"),
        })
