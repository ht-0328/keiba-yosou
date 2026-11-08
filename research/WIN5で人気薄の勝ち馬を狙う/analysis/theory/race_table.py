"""出走の表から、1行 = 1レースの表（レースの条件・人気の割れ方・勝ち馬の人気・人気薄が勝ったか）を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: レースで1つに決まる列（出走の表の列）。
RACE_COLUMNS: tuple[str, ...] = (
    "race_date", "year", "venue", "surface", "distance_m", "condition", "class_name", "weight_type", "field_size",
    "favorite_odds", "contenders", "top3_market", "longshot_market", "win5_leg",
)


@dataclass(frozen=True)
class RaceTable:
    """``longshot_from`` 番人気以下の馬が勝ったレースに ``longshot_won`` を立てる。勝ち馬の人気は ``winner_popularity``。"""

    longshot_from: int = 10

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        races = runners.groupby("race_id")[list(RACE_COLUMNS)].first()
        winners = runners.loc[runners["finish"] == 1].drop_duplicates("race_id").set_index("race_id")["popularity"]
        races["winner_popularity"] = winners.reindex(races.index)
        races["longshot_won"] = races["winner_popularity"] >= self.longshot_from
        return races.loc[races["winner_popularity"].notna()]
