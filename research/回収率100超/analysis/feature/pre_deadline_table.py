"""締め切り前に手に入る材料だけのモデルの、特徴量の選び方と、締め切り前のオッズでの材料の作り直し。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .learning_table import PLACE_BASELINE, POOL_COLUMNS, WIN_BASELINE, LearningTable
from .pool_features import PoolFeatures

#: 過去のレースでも締め切り前の断面が取れるプールから作る列（時系列オッズがあるのは単複枠と馬連だけ）。
PRE_DEADLINE_POOLS: tuple[str, ...] = ("複勝から見た3着以内率", "馬連から見た2着以内率")
#: 締め切り前のオッズで置き換える、出走の表の列。
_ODDS_COLUMNS = ("win_odds", "place_odds_low", "place_odds_high")


class PreDeadlineTable:
    """締め切り前に手に入る材料だけで学習・予測するための表を作る。

    研究のモデルの材料のうち、3連単・馬単・3連複・ワイドのオッズと票数は、過去のレースの締め切り前の値が
    手に入らない（時系列オッズは単複枠と馬連だけ。票数の時系列は無い）。そこで、その列を外したモデルを
    確定オッズで学習し、予測するときだけ材料を締め切り前のオッズで作り直す。
    作り直すのは、単勝から見た勝率・単勝から見た複勝率・複勝と馬連から見た確率と、そこから作る列（log・順位・差）。
    騎手などの超過成績・マイニング予想・馬の実力の列は、そのレースより前の情報なので作り直さない。
    """

    def __init__(self, learning: LearningTable) -> None:
        self._learning = learning
        self._excluded = tuple(column for column in POOL_COLUMNS if column not in PRE_DEADLINE_POOLS)

    def features(self, features: list[str]) -> list[str]:
        """``features`` から、締め切り前に手に入らないプールから作った列を外す。"""
        return [feature for feature in features if not any(name in feature for name in self._excluded)]

    def rebuild(self, rows: pd.DataFrame, win_place: pd.DataFrame, quinella: pd.DataFrame) -> pd.DataFrame:
        """``rows``（確定オッズで作った学習の表の一部）の市場の列を、締め切り前の断面で作り直した表。

        出走した馬のうち1頭でも締め切り前の単勝・複勝・馬連の値が欠けるレースは、比べられないので落とす。
        """
        frame = rows.drop(columns=[*_ODDS_COLUMNS, PRE_DEADLINE_POOLS[1]]).merge(
            win_place[["rid", "horse_no", *_ODDS_COLUMNS]], on=["rid", "horse_no"], how="left")
        frame = frame.merge(quinella, on=["rid", "horse_no"], how="left")
        frame = frame[~frame["rid"].isin(self._incomplete_races(frame))].reset_index(drop=True)
        frame[WIN_BASELINE] = self._share(1.0 / frame["win_odds"], frame["rid"])
        frame = self._learning.add_market_place_rate(frame)
        middle = (frame["place_odds_low"] + frame["place_odds_high"]) / 2.0
        frame[PRE_DEADLINE_POOLS[0]] = self._share(1.0 / middle, frame["rid"])
        frame, _ = PoolFeatures(PRE_DEADLINE_POOLS, WIN_BASELINE, PLACE_BASELINE).add_to(frame)
        return frame

    @staticmethod
    def _incomplete_races(frame: pd.DataFrame) -> np.ndarray:
        needed = frame[[*_ODDS_COLUMNS, PRE_DEADLINE_POOLS[1]]]
        return frame.loc[needed.isna().any(axis=1) | (needed <= 0).any(axis=1), "rid"].unique()

    @staticmethod
    def _share(values: pd.Series, race: pd.Series) -> pd.Series:
        return values / values.groupby(race).transform("sum")
