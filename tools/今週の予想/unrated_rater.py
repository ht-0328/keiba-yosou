"""評価できない馬（中央の過去走が無い招待馬）の確率を、過去の同じ種類の招待馬の成績で置き換える。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.filter_columns import MEMBERS, member_column
from 今週の予想.forecast_columns import (
    HORSE_ID,
    DANGER_SCORE,
    INVITED_NOTE,
    IS_DANGER,
    OUT_PROBABILITY,
    PLACE_VALUE,
    PROBABILITY,
    UNRATED,
    WIN_ODDS,
    WIN_PROBABILITY,
    WIN_VALUE,
)
from 今週の予想.invited_rates import InvitedRates


class UnratedRater:
    """1レースの表の、評価できない馬（列 ``unrated`` が真）の確率を ``InvitedRates`` の評価で置き換え、印の候補に戻す。

    - 3着以内に入る確率と1着になる確率を、評価の値にする（モデルごとの列も同じ値）。
    - 複勝の期待値は、見込みの払戻の倍率をそのままに、3着以内の確率の比で直す。単勝の期待値は、1着になる確率 × 単勝オッズ。
    - 評価した馬は ``unrated`` を偽にして、列 ``invited_note`` に評価の文を入れる。危険な人気馬（消）の判定と危険度は、人気馬の予想の材料が空なので使わない。
    - 人気（単勝オッズ）が無い時点（木曜）や、評価の基準が無い馬は、評価できない馬のまま（印と買い目の候補から外れる）。
    """

    def __init__(self, rates: InvitedRates | None) -> None:
        self._rates = rates

    def rate(self, race: pd.DataFrame, race_date: str) -> pd.DataFrame:
        """``race`` は1レースの表（馬ID・オッズ・確率・期待値の列）。``race_date`` は YYYY-MM-DD。直した表のコピーを返す。"""
        table = race.copy()
        table[INVITED_NOTE] = None
        if self._rates is None or UNRATED not in table.columns or WIN_ODDS not in table.columns:
            return table
        unrated = table[UNRATED].fillna(False).astype(bool)
        popularity = pd.to_numeric(table[WIN_ODDS], errors="coerce").rank(method="min")
        for index in table.index[unrated & popularity.notna()]:
            rate = self._rates.rate(str(table.at[index, HORSE_ID]), popularity.at[index], race_date)
            if rate is not None:
                self._replace(table, index, rate.top3, rate.win)
                table.at[index, INVITED_NOTE] = rate.note()
        return table

    def _replace(self, table: pd.DataFrame, index, top3: float, win: float) -> None:
        odds = float(table.at[index, WIN_ODDS])
        for name, always in ((_same, True), *((_member(member), False) for member in MEMBERS)):
            probability, place_value = name(PROBABILITY), name(PLACE_VALUE)
            if place_value in table.columns and probability in table.columns:
                old = float(table.at[index, probability])
                table.at[index, place_value] = float(table.at[index, place_value]) * top3 / old if old > 0 else np.nan
            for column, value in ((probability, top3), (name(WIN_PROBABILITY), win), (name(WIN_VALUE), win * odds)):
                if always or column in table.columns:
                    table.at[index, column] = value
        table.at[index, UNRATED] = False
        if IS_DANGER in table.columns:
            table.at[index, IS_DANGER] = False
        for column in (OUT_PROBABILITY, DANGER_SCORE):
            if column in table.columns:
                table.at[index, column] = np.nan


def _same(base: str) -> str:
    """2つのモデルの平均の列の名前（そのまま）。"""
    return base


def _member(member: str):
    """モデルごとの列の名前を作る関数。"""
    return lambda base: member_column(base, member)
