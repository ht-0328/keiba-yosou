"""1レースの全頭に印（◎○▲△☆注消）を付ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 今週の予想.forecast_columns import (
    HORSE_NO,
    MARK,
    MARK_REASON,
    MARKET_TOP3,
    PLACE_VALUE,
    POPULARITY,
    PROBABILITY,
    RANK,
    UPDOWN,
    WIN_ODDS,
)

#: 3着以内の確率の順位で付ける印（1位から順）。△は 4〜6位の3頭（利用者の指示「白三角は3点で」）。
RANK_MARKS: tuple[str, ...] = ("◎", "○", "▲", "△", "△", "△")
VALUE_MARK = "☆"
NOTE_MARK = "注"
#: 印の付かなかった馬（買わない馬）の印。利用者の決定（2026-10-03）。
OUT_MARK = "消"
#: 印の並び（画面の凡例と、並べ替えに使う）。
MARK_ORDER: tuple[str, ...] = ("◎", "○", "▲", "△", VALUE_MARK, NOTE_MARK, OUT_MARK)
#: ☆ を付ける複勝の期待値の下限（設計書「買うレースと買い目を決める」07 の 2。研究「回収率100超」で決めた買う線）。
VALUE_LINE = 1.25
#: 人気馬の範囲を広げる頭数（13頭以下は1〜3番人気、14頭以上は1〜5番人気。設計書 07 の 3）。
WIDE_FIELD = 14
_FAVORITES_SMALL = 3
_FAVORITES_WIDE = 5


class MarkRule:
    """1レースの全頭に印を付ける（設計書「買うレースと買い目を決める」07 の 5 の印に、利用者の決定で「消」を足したもの）。

    - ◎○▲: 3着以内の確率の 1〜3位。△: 4〜6位の3頭。
    - ☆: 穴馬（人気馬の範囲より下の人気）のうち、◎〜△ の付いていない馬で、複勝の期待値がいちばん高い馬。
      期待値が ``VALUE_LINE``（1.25）以上のときだけ。オッズの無い時点（木曜）は付けない。
    - 注: 印の無い馬のうち、上げ下げ（logit(予想) − logit(市場の見立て)）がいちばん大きい馬。上げ下げが正（市場より来ると見る）のときだけ。
      オッズの無い時点（木曜）は付けない。
    - 消: ほかの全部の馬（買わない馬）。

    危険な人気馬（設計書 07 の 3）の判定は、まだ使っていない。
    """

    def assign(self, race: pd.DataFrame) -> pd.DataFrame:
        """``race`` は1レースの表（列 ``horse_no``・``probability``。前日・当日は ``win_odds``・``market_top3``・``place_value`` も）。

        戻り値は ``race`` に列 ``rank``・``popularity``・``updown``・``mark``・``mark_reason`` を足し、3着以内の確率の高い順
        （同じなら馬番の小さい順）に並べた表。
        """
        table = race.copy()
        for column in (WIN_ODDS, MARKET_TOP3, PLACE_VALUE):
            if column not in table.columns:
                table[column] = np.nan
        table = table.sort_values([PROBABILITY, HORSE_NO], ascending=[False, True], na_position="last").reset_index(drop=True)
        table[RANK] = np.arange(1, len(table) + 1)
        table[POPULARITY] = table[WIN_ODDS].rank(method="min")
        table[UPDOWN] = _logit(table[PROBABILITY]) - _logit(table[MARKET_TOP3])
        table[MARK] = OUT_MARK
        table[MARK_REASON] = ""
        for row, mark in zip(range(len(table)), RANK_MARKS, strict=False):
            table.loc[row, MARK] = mark
            table.loc[row, MARK_REASON] = f"3着以内に入る確率がレース内{row + 1}位"
        self._mark_value(table)
        self._mark_note(table)
        unmarked = table[MARK] == OUT_MARK
        table.loc[unmarked, MARK_REASON] = table.loc[unmarked].apply(self._out_reason, axis=1)
        return table

    def _mark_value(self, table: pd.DataFrame) -> None:
        """穴馬で、複勝の期待値がいちばん高い馬に ☆（線以上のときだけ）。"""
        favorites = _favorite_count(len(table))
        candidates = table[(table[MARK] == OUT_MARK) & (table[POPULARITY] > favorites)][PLACE_VALUE].dropna()
        if candidates.empty or candidates.max() < VALUE_LINE:
            return
        row = candidates.idxmax()
        table.loc[row, MARK] = VALUE_MARK
        table.loc[row, MARK_REASON] = (f"穴馬（{table.loc[row, POPULARITY]:.0f}番人気）の中で複勝の期待値がいちばん高く、"
                                       f"{table.loc[row, PLACE_VALUE]:.2f} が線の {VALUE_LINE:.2f} 以上")

    def _mark_note(self, table: pd.DataFrame) -> None:
        """印の無い馬のうち、市場より来ると見る度合いがいちばん大きい馬に 注（正のときだけ）。"""
        candidates = table[table[MARK] == OUT_MARK][UPDOWN].dropna()
        if candidates.empty or candidates.max() <= 0:
            return
        row = candidates.idxmax()
        table.loc[row, MARK] = NOTE_MARK
        table.loc[row, MARK_REASON] = (f"印の無い馬の中で、市場の見立て（{table.loc[row, MARKET_TOP3]:.1%}）より来ると見る度合いが"
                                       f"いちばん大きい（予想 {table.loc[row, PROBABILITY]:.1%}）")

    def _out_reason(self, row: pd.Series) -> str:
        """消になった理由。"""
        reason = f"3着以内に入る確率がレース内{row[RANK]:.0f}位で、◎〜△（{len(RANK_MARKS)}位まで）に入らない"
        if pd.notna(row[PLACE_VALUE]):
            reason += f"。複勝の期待値 {row[PLACE_VALUE]:.2f} も☆の条件に当たらない"
        return reason


def _favorite_count(field_size: int) -> int:
    """人気馬とみなす人気の範囲（何番人気まで）。"""
    return _FAVORITES_WIDE if field_size >= WIDE_FIELD else _FAVORITES_SMALL


def _logit(values: pd.Series) -> pd.Series:
    clipped = values.astype(float).clip(1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))
