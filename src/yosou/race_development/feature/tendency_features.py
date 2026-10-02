"""V. 既存の予想から見た傾向（1頭ごと 16個・1レースごと 11個）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_ID

from .group_forecast import (
    FAVORITE_OUT_PROBABILITY,
    LONGSHOT_TOP3_PROBABILITY,
    TOP3_PROBABILITY,
    UPSET_BETS,
    GroupForecast,
    big_upset_probability,
    calm_probability,
)
from .race_order_statistic import RaceOrderStatistic

#: 1頭ごとの特徴量の名前（1頭ごとだけのもの）。
TOP3 = "既存の予想の3着以内の確率"
TOP3_RANK = "既存の予想の3着以内の確率のレース内順位"
TOP3_GAP = "既存の予想の3着以内の確率の1位との差"
FAVORITE_OUT = "既存の予想の人気馬が4着以下になる確率"
LONGSHOT_TOP3 = "既存の予想の穴馬が3着以内に入る確率"
#: 1レースごとの特徴量の名前（1頭ごとの行にも配る）。
TOP3_LEADING_GAP = "既存の予想の3着以内の確率の1位と2位の差"
FAVORITE_OUT_MAX = "既存の予想の人気馬が4着以下になる確率の最大"
LONGSHOT_TOP3_MAX = "既存の予想の穴馬が3着以内に入る確率の最大"


def calm_feature(bet_label: str) -> str:
    """その券種の荒れ具合が「固い」の確率の特徴量の名前。"""
    return f"既存の予想の荒れ具合（{bet_label}）が固い確率"


def big_upset_feature(bet_label: str) -> str:
    """その券種の荒れ具合が「大荒れ」か「超荒れ」の確率の特徴量の名前。"""
    return f"既存の予想の荒れ具合（{bet_label}）が大荒れ以上の確率"


#: 学習データに入れるには、値が要る列。人気馬・穴馬の確率は、その馬しか予測しないので、欠損値のままモデルに渡す。
REQUIRED_HORSE_FEATURES: tuple[str, ...] = (TOP3, *(calm_feature(label) for label in UPSET_BETS.values()))
REQUIRED_RACE_FEATURES: tuple[str, ...] = (TOP3_LEADING_GAP, *(calm_feature(label) for label in UPSET_BETS.values()))


class TendencyFeatures:
    """V. 傾向の組（既存の予想）の予測から、前半・後半・着順の予想の特徴量を作る（設計書 09 の V）。

    「このメンバーでは、この馬が 3着以内に入りそうか」「人気馬が危ないか」「穴馬が来そうか」「レースが荒れそうか」を、
    展開の予想の材料にする。渡す予測は、そのサンプルを学習に使っていない既存の予想のモデルの予測である（設計書 11 の決まり 11）。
    人気馬の4着以下の確率は人気馬だけ、穴馬の3着以内の確率は穴馬だけにあり、ほかの馬は欠損値になる。
    その時点で既存の予想がモデルを持たない列（木曜の人気馬・穴馬）は、全部が欠損値になる。
    """

    def __init__(self) -> None:
        self._order = RaceOrderStatistic()

    def horse(self, ids: pd.DataFrame, tendency: GroupForecast) -> pd.DataFrame:
        """1頭ごとの 16個。``ids`` は学習データ（予測用データ）の ID 列。index は ``ids`` と同じ。"""
        horses = tendency.horse_rows(ids)
        race = ids[RACE_ID]
        top3 = self._column(horses, TOP3_PROBABILITY)
        leading = self._order.nth_for_rows(top3, race, 1, largest=True)
        own = pd.DataFrame({
            TOP3: top3,
            TOP3_RANK: top3.groupby(race).rank(method="min", ascending=False),
            TOP3_GAP: top3 - leading,
            FAVORITE_OUT: self._column(horses, FAVORITE_OUT_PROBABILITY),
            LONGSHOT_TOP3: self._column(horses, LONGSHOT_TOP3_PROBABILITY),
        }, index=ids.index)
        return pd.concat([own, self.race(ids, tendency)], axis=1)

    def race(self, ids: pd.DataFrame, tendency: GroupForecast) -> pd.DataFrame:
        """1レースごとの 11個。``ids`` は、列 ``レースID`` のある ID 列（1頭ごとでも1レースごとでもよい）。"""
        races = tendency.race_rows(ids)
        keys = ids[RACE_ID].astype("str").to_numpy()
        horses = tendency.horses
        race = horses[RACE_ID].astype("str")
        top3 = self._column(horses, TOP3_PROBABILITY)
        gap = self._order.nth(top3, race, 1, largest=True) - self._order.nth(top3, race, 2, largest=True)
        upsets: dict[str, pd.Series] = {}
        for key, label in UPSET_BETS.items():
            upsets[calm_feature(label)] = self._column(races, calm_probability(key))
            upsets[big_upset_feature(label)] = self._column(races, big_upset_probability(key))
        return pd.DataFrame({
            **upsets,
            TOP3_LEADING_GAP: gap.reindex(keys).to_numpy(),
            FAVORITE_OUT_MAX: self._column(horses, FAVORITE_OUT_PROBABILITY).groupby(race).max().reindex(keys).to_numpy(),
            LONGSHOT_TOP3_MAX: self._column(horses, LONGSHOT_TOP3_PROBABILITY).groupby(race).max().reindex(keys).to_numpy(),
        }, index=ids.index)

    def _column(self, table: pd.DataFrame, name: str) -> pd.Series:
        """``table`` の列。その時点で予測していない既存の予想の列は、全部が欠損値の列にする。"""
        if name not in table.columns:
            return pd.Series(np.nan, index=table.index, dtype="float64")
        return pd.to_numeric(table[name], errors="coerce")
