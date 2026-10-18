"""印を付けた表から、買うレースを絞るのに使うレースの中身を1行 = 1レースで作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.forecast_columns import MARK, WIN_ODDS, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.race_condition import FAVORITE_ODDS, FIELD_SIZE, TOP_VALUE


class ComboRaceTraits:
    """印を付けた表（1行 = 1頭。何レースぶんでもよい）から、列 ``race_id`` と ``TRAIT_COLUMNS``（``race_condition``）の表を作る。
    研究「レースの種類ごとの買い方」の docs/03 の 3 と同じ作り。

    頭数は列 ``field_size`` があればその値、無ければそのレースの行の数。1番人気の単勝オッズはそのレースの単勝オッズの最小、
    ◎ の単勝の期待値は ◎ の馬の ``win_value``。列が無いか値が無ければ欠損値（その中身で絞る決まりでは買わない）。
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
        table = pd.DataFrame({FIELD_SIZE: field.astype(float), FAVORITE_ODDS: favorite.astype(float), TOP_VALUE: top.astype(float)})
        return table.rename_axis("race_id").reset_index()
