"""印を付けた表から、買うレースを絞るのに使うレースの中身を1行 = 1レースで作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.filter_columns import AGREEMENT, member_columns
from 今週の予想.forecast_columns import IS_DANGER, MARK, MARKET_WIN, WIN_ODDS, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.race_condition import AGREED, FAVORITE_ODDS, FIELD_SIZE, HAS_DANGER, TOP3_SHARE, TOP_VALUE


#: 2モデル一致の線（道具「印の成績」の ``BacktestMarker`` と同じ 1.00）。
AGREEMENT_LINE = 1.0


class ComboRaceTraits:
    """印を付けた表（1行 = 1頭。何レースぶんでもよい）から、列 ``race_id`` と ``TRAIT_COLUMNS``（``race_condition``）の表を作る。
    研究「レースの種類ごとの買い方」の docs/03 の 3 と同じ作り。

    頭数は列 ``field_size`` があればその値、無ければそのレースの行の数。1番人気の単勝オッズはそのレースの単勝オッズの最小、
    ◎ の単勝の期待値は ◎ の馬の ``win_value``、市場の勝率の上位3頭の和は ``market_win`` の大きい3頭の和、危険な人気馬は ``is_danger`` が
    真の馬がいれば 1、2モデル一致は ◎ のモデルごとの単勝の期待値（``win_value_lightgbm``・``win_value_catboost``）がどちらも
    ``AGREEMENT_LINE`` 以上なら 1（その列が無ければ ``agreement`` が真なら 1。道具「印の成績」の 2モデル一致と同じ）。列が無いか値が無ければ欠損値（その中身で絞る決まりでは買わない）。
    例: 単勝オッズが 1.8・4.0・9.5 倍の3頭で、◎ の単勝の期待値が 0.95 なら、頭数 3・1番人気 1.8倍・◎ の期待値 0.95。
    """

    def of(self, marked: pd.DataFrame) -> pd.DataFrame:
        frame = marked.assign(race_id=marked["race_id"].astype(str))
        race = frame.groupby("race_id", sort=False)
        field = race[FIELD_SIZE].first() if FIELD_SIZE in frame.columns else race.size()
        favorite = race[WIN_ODDS].min() if WIN_ODDS in frame.columns else pd.Series(np.nan, index=field.index)
        if MARK in frame.columns and WIN_VALUE in frame.columns:
            top = frame[frame[MARK] == TOP_MARK].groupby("race_id")[WIN_VALUE].first().reindex(field.index)
        else:
            top = pd.Series(np.nan, index=field.index)
        table = pd.DataFrame({FIELD_SIZE: field.astype(float), FAVORITE_ODDS: favorite.astype(float), TOP_VALUE: top.astype(float),
                              TOP3_SHARE: self._column(race, MARKET_WIN, lambda values: values.nlargest(3).sum(), field.index),
                              HAS_DANGER: self._column(race, IS_DANGER, lambda values: float(values.fillna(False).astype(bool).any()), field.index),
                              AGREED: self._agreed(frame, race, field.index)})
        return table.rename_axis("race_id").reset_index()

    def _agreed(self, frame: pd.DataFrame, race, index: pd.Index) -> pd.Series:
        """2モデル一致のレースなら 1。◎ のモデルごとの単勝の期待値が無ければ、列 ``agreement`` から（それも無ければ欠損値）。"""
        names = list(member_columns(WIN_VALUE))
        if MARK in frame.columns and all(name in frame.columns for name in names):
            tops = frame[frame[MARK] == TOP_MARK].groupby("race_id")[names].first()
            agreed = (tops >= AGREEMENT_LINE).all(axis=1) & tops.notna().all(axis=1)
            return agreed.astype(float).reindex(index).fillna(0.0)
        return self._column(race, AGREEMENT, lambda values: float(values.fillna(False).astype(bool).any()), index)

    @staticmethod
    def _column(race, column: str, how, index: pd.Index) -> pd.Series:
        """レースごとの値（列が無ければ欠損値）。"""
        if column not in race.obj.columns:
            return pd.Series(np.nan, index=index)
        return race[column].apply(how).astype(float).reindex(index)
