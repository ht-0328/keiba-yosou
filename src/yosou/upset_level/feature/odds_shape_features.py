"""B. オッズの形（10個）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import RaceRecords, as_numbers
from yosou.shared.feature.group import MARKET_WIN_RATE, WIN_ODDS

#: 特徴量の名前。1番人気のオッズは、予測に要る情報の確認と評価の基準にも使うので、外にも見せる。
FAVORITE_ODDS = "1番人気のオッズ"
SECOND_ODDS = "2番人気のオッズ"
THIRD_ODDS = "3番人気のオッズ"
FIFTH_ODDS = "5番人気のオッズ"
SECOND_TO_FIRST = "1番人気と2番人気のオッズの比"
UPPER_MAX_ODDS = "2〜5番人気の最大オッズ"
UNDER_TEN_COUNT = "単勝10倍未満の頭数"
TOP3_MARKET_RATE = "市場勝率の上位3頭の合計"
MARKET_ENTROPY = "市場勝率のエントロピー"
LONGEST_ODDS = "最低人気のオッズ"
NAMES: tuple[str, ...] = (
    FAVORITE_ODDS, SECOND_ODDS, THIRD_ODDS, FIFTH_ODDS, SECOND_TO_FIRST, UPPER_MAX_ODDS,
    UNDER_TEN_COUNT, TOP3_MARKET_RATE, MARKET_ENTROPY, LONGEST_ODDS,
)
#: 「有力馬」とみなす単勝オッズの上限（10倍未満）と、「2〜5番人気」の範囲、市場勝率を足す上位の頭数。
_UNDER_ODDS = 10.0
_UPPER_FROM, _UPPER_TO = 2, 5
_TOP_COUNT = 3


class OddsShapeFeatures:
    """B. オッズの形。全頭の単勝オッズから、強い馬が抜けているか・有力馬が何頭いるかを表す。``RaceFeatureGroup`` を守る。

    材料は1頭ごとの特徴量 J（単勝オッズ・オッズから見た勝率）。学習では確定オッズ、予測では締め切り前のオッズか
    利用者が渡したオッズになる（設計書 07）。オッズの無いレース（木曜）は、全部欠損値。
    """

    def build(self, records: RaceRecords) -> pd.DataFrame:
        entries = records.entries
        odds = as_numbers(records.horse_features[WIN_ODDS])
        rate = as_numbers(records.horse_features[MARKET_WIN_RATE])
        known = odds.notna()
        ordered = pd.DataFrame({
            "race": entries.loc[known, "race_id"], "odds": odds[known], "rate": rate[known],
        }).sort_values(["race", "odds"], kind="stable")
        ordered["rank"] = ordered.groupby("race").cumcount() + 1
        by_rank = ordered.pivot(index="race", columns="rank", values="odds")
        by_race = ordered.groupby("race")
        first, second = self._nth(by_rank, 1), self._nth(by_rank, 2)
        return pd.DataFrame({
            FAVORITE_ODDS: first,
            SECOND_ODDS: second,
            THIRD_ODDS: self._nth(by_rank, 3),
            FIFTH_ODDS: self._nth(by_rank, _UPPER_TO),
            SECOND_TO_FIRST: second / first,
            UPPER_MAX_ODDS: self._upper_max(by_rank),
            UNDER_TEN_COUNT: by_race["odds"].apply(lambda values: float((values < _UNDER_ODDS).sum())),
            TOP3_MARKET_RATE: ordered[ordered["rank"] <= _TOP_COUNT].groupby("race")["rate"].sum(),
            MARKET_ENTROPY: by_race["rate"].apply(self._entropy),
            LONGEST_ODDS: by_race["odds"].max(),
        }).reindex(records.race_ids)

    def _nth(self, by_rank: pd.DataFrame, rank: int) -> pd.Series:
        """小さい順の ``rank`` 番目のオッズ。その頭数に満たないレースは欠損値。"""
        if rank in by_rank.columns:
            return by_rank[rank]
        return pd.Series(np.nan, index=by_rank.index, dtype="float64")

    def _upper_max(self, by_rank: pd.DataFrame) -> pd.Series:
        """2〜5番人気の最大のオッズ。"""
        columns = [rank for rank in range(_UPPER_FROM, _UPPER_TO + 1) if rank in by_rank.columns]
        if not columns:
            return pd.Series(np.nan, index=by_rank.index, dtype="float64")
        return by_rank[columns].max(axis=1)

    def _entropy(self, rates: pd.Series) -> float:
        """市場勝率のエントロピー（頭数の対数で割って 0〜1 にする）。1頭なら 0。"""
        values = rates.dropna().to_numpy()
        values = values[values > 0]
        if len(values) <= 1:
            return 0.0
        return float(-(values * np.log(values)).sum() / np.log(len(values)))
