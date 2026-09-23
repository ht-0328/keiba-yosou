"""3つの1頭ごとの予測を、1行 = 1頭の表にする。"""

from __future__ import annotations

import pandas as pd

from .. import column_names as names


class RunnerTableBuilder:
    """近走と適性（全頭）・人気馬（人気馬だけ）・穴馬（穴馬だけ）の予測を (レースID, 馬番) で結合し、英語の列名にする。

    人気馬でない馬の ``danger_prob`` と、穴馬でない馬の ``longshot_prob``・``longshot_zone`` は欠損になる。
    """

    def build(self, form: pd.DataFrame, favorites: pd.DataFrame, longshots: pd.DataFrame) -> pd.DataFrame:
        runners = form[[*names.RUNNER_BASE_COLUMNS, names.FORM_PROBABILITY_JA]].rename(
            columns={**names.RUNNER_BASE_COLUMNS, names.FORM_PROBABILITY_JA: names.FORM_PROB},
        )
        danger = favorites[[names.RACE_ID_JA, names.HORSE_NO_JA, names.DANGER_PROBABILITY_JA]].rename(
            columns={names.RACE_ID_JA: names.RACE_ID, names.HORSE_NO_JA: names.HORSE_NO,
                     names.DANGER_PROBABILITY_JA: names.DANGER_PROB},
        )
        longshot = longshots[[names.RACE_ID_JA, names.HORSE_NO_JA, names.LONGSHOT_PROBABILITY_JA, names.LONGSHOT_ZONE_JA]].rename(
            columns={names.RACE_ID_JA: names.RACE_ID, names.HORSE_NO_JA: names.HORSE_NO,
                     names.LONGSHOT_PROBABILITY_JA: names.LONGSHOT_PROB, names.LONGSHOT_ZONE_JA: names.LONGSHOT_ZONE},
        )
        keys = [names.RACE_ID, names.HORSE_NO]
        merged = runners.merge(danger, on=keys, how="left").merge(longshot, on=keys, how="left")
        return merged.sort_values(keys).reset_index(drop=True)
