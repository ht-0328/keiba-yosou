"""出走の表から、1行 = 1レースの表（切り口と、大穴の来方）を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: レースの決着の分け方（大穴が3着以内に2頭以上 → 大穴1着だけ → そのほか の順に1つに決める）。
MULTI, WIN_ONLY, OTHER = "大穴2頭以上", "大穴1着（2頭目なし）", "そのほか"

_FIRST_COLUMNS: tuple[str, ...] = (
    "race_date", "year", "venue", "surface", "course", "distance_m", "condition", "class_name", "weight_type", "handicap",
    "field_size", "period", "pace", "forecast_pace", "forecast_band", "pace_vs_forecast", "p_high", "p_slow",
    "tilt_inner", "tilt_front", "carried_spread", "first3f", "last3f_race",
)


@dataclass(frozen=True)
class RaceTable:
    """``runners``（``RunnerEnrichment`` の表）から、レースごとに次の列を作る（index は race_id）。

    - ``longshot_won``: 大穴（10番人気以下）が1着 / ``longshot_top3``: 3着以内の大穴の頭数
    - ``longshot_multi``: 大穴が3着以内に2頭以上 / ``longshot_all``: 1〜3着が全部大穴
    - ``outcome``: 決着の分け方（大穴2頭以上・大穴1着（2頭目なし）・そのほか）
    - ``longshot_market``: 大穴のオッズから見た勝率の合計（単勝オッズの逆数をレースの中で合計 1 にそろえて足したもの）
    - ``favorite_finish``: 1番人気の着順 / 切り口の列（開催日・競馬場・芝ダ・距離・馬場・クラス・重量種別・頭数・ペース …）
    - ``pre_close_longshot_won``: 締め切り前の人気で10番人気以下の馬が1着（断面のあるレースだけ。無ければ欠損値）
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.assign(
            longshot_top3_flag=runners["longshot"] & (runners["top3"] > 0),
            longshot_win_flag=runners["longshot"] & (runners["won"] > 0),
            implied=1.0 / runners["win_odds"].where(runners["win_odds"] > 0),
        )
        frame["market_share"] = frame["implied"] / frame.groupby("race_id")["implied"].transform("sum")
        race = frame.groupby("race_id", sort=True)
        table = race[list(_FIRST_COLUMNS)].first()
        table["longshot_won"] = race["longshot_win_flag"].any()
        table["longshot_top3"] = race["longshot_top3_flag"].sum().astype(int)
        table["longshot_multi"] = table["longshot_top3"] >= 2
        table["longshot_all"] = table["longshot_top3"] >= 3
        table["outcome"] = np.select([table["longshot_multi"], table["longshot_won"]], [MULTI, WIN_ONLY], default=OTHER)
        table["longshot_market"] = frame["market_share"].where(frame["longshot"], 0.0).groupby(frame["race_id"]).sum()
        favorites = frame.loc[frame["popularity"] == 1].drop_duplicates("race_id").set_index("race_id")
        table["favorite_finish"] = favorites["finish"].reindex(table.index)
        table["pre_close_longshot_won"] = self._pre_close_won(frame).reindex(table.index)
        return table

    @staticmethod
    def _pre_close_won(frame: pd.DataFrame) -> pd.Series:
        known = frame.loc[frame["pre_close_longshot"].notna()]
        flag = known["pre_close_longshot"].astype(bool) & (known["won"] > 0)
        return flag.groupby(known["race_id"]).any().astype(object)
