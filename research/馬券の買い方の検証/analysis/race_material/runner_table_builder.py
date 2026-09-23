"""3つの1頭ごとの予測を、1行 = 1頭の表にする。"""

from __future__ import annotations

import pandas as pd

from .. import column_names as names


#: 複勝の確定オッズの表（``FinalOddsRepository(PLACE).read``）の列。
_ODDS_RACE_ID, _ODDS_COMBO, _ODDS_VALUE = "race_id", "combo", "odds"


class RunnerTableBuilder:
    """近走と適性（全頭）・人気馬（人気馬だけ）・穴馬（穴馬だけ）の予測を (レースID, 馬番) で結合し、英語の列名にする。

    人気馬でない馬の ``danger_prob`` と、穴馬でない馬の ``longshot_prob``・``longshot_zone`` は欠損になる。
    ``place_odds``（複勝の確定オッズ。``FinalOddsRepository`` の表）を渡すと、下限のオッズを ``place_odds`` 列に付ける。
    """

    def build(self, form: pd.DataFrame, favorites: pd.DataFrame, longshots: pd.DataFrame,
              place_odds: pd.DataFrame | None = None) -> pd.DataFrame:
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
        merged = merged.merge(self._place_odds(place_odds), on=keys, how="left")
        return merged.sort_values(keys).reset_index(drop=True)

    def _place_odds(self, place_odds: pd.DataFrame | None) -> pd.DataFrame:
        """複勝の確定オッズの表を (レースID, 馬番, place_odds) にする。無ければ空（列は欠損になる）。"""
        if place_odds is None or place_odds.empty:
            return pd.DataFrame({names.RACE_ID: pd.Series(dtype=str), names.HORSE_NO: pd.Series(dtype="int64"),
                                 names.PLACE_ODDS: pd.Series(dtype=float)})
        return pd.DataFrame({
            names.RACE_ID: place_odds[_ODDS_RACE_ID].astype(str), names.HORSE_NO: place_odds[_ODDS_COMBO].astype(int),
            names.PLACE_ODDS: place_odds[_ODDS_VALUE].astype(float),
        })
