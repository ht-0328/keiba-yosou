"""出走の行から、レースごとの結果（評価用の列）をまとめる。"""

from __future__ import annotations

import pandas as pd

from ..feature import as_numbers
from . import column_names as names

#: 3着以内に入った着順のうち、いちばん大きいもの。
_LAST_PLACE = 3
#: 「2〜5番人気」の人気の範囲（オッズの小さい順の 2番目から 5番目）。
_UPPER_FROM, _UPPER_TO = 2, 5


class RaceResultSummary:
    """出走の行（1行 = 1頭）から、レースごとの結果を 1行 = 1レースにまとめる（荒れ具合の設計書 08 の 2）。

    どれもそのレースの結果なので、評価用の列にだけ使い、特徴量にはしない（荒れ具合の設計書 11 の 6）。
    1番人気は、確定の単勝オッズが最小の馬（同じ作り方で予測のときの1番人気を決める。荒れ具合の設計書 11 の 9）。
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        """列は勝ち馬の人気・1〜3着の人気の和・1番人気の確定着順と確定オッズ・2〜5番人気の最大の確定オッズ・確定の出走頭数。
        index はレースID（``runners`` に出てきた順）。値が無ければ欠損値。
        """
        race = runners["race_id"]
        finish = as_numbers(runners["finish"])
        popularity = as_numbers(runners["popularity"])
        odds = as_numbers(runners["win_odds"])
        race_ids = pd.Index(race.drop_duplicates())
        favorite = self._favorite_rows(race, odds)
        return pd.DataFrame({
            names.WINNER_POPULARITY: popularity.where(finish == 1).groupby(race).min(),
            names.TOP3_POPULARITY_SUM: popularity.where(finish <= _LAST_PLACE).groupby(race).sum(min_count=1),
            names.FAVORITE_FINISH: finish.loc[favorite].set_axis(favorite.index),
            names.FAVORITE_ODDS: odds.loc[favorite].set_axis(favorite.index),
            names.UPPER_MAX_ODDS: self._upper_max_odds(race, odds),
            names.FIELD_SIZE: race.groupby(race).size(),
        }).reindex(race_ids)

    def _favorite_rows(self, race: pd.Series, odds: pd.Series) -> pd.Series:
        """レースID → 単勝オッズが最小の馬の行（index）。オッズの無いレースは入らない。"""
        known = odds.notna()
        return odds[known].groupby(race[known]).idxmin()

    def _upper_max_odds(self, race: pd.Series, odds: pd.Series) -> pd.Series:
        """レースID → 2〜5番人気（オッズの小さい順の 2〜5番目）のうち最大のオッズ。"""
        known = odds.notna()
        ordered = pd.DataFrame({"race": race[known], "odds": odds[known]}).sort_values(["race", "odds"], kind="stable")
        rank = ordered.groupby("race").cumcount() + 1
        upper = ordered[rank.between(_UPPER_FROM, _UPPER_TO)]
        return upper.groupby("race")["odds"].max()
