"""地方で採用している買い方から、1レースで実際に買う買い目を決める。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, PLACE_VALUE, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.ticket_rules import PLACE_VALUE_LINE

from 発走前の通知.local_bets import LocalBets

#: 単勝を買う ◎ の単勝の期待値の線（地方で採用している買い方。当日の時点だけ）。
WIN_VALUE_LINE = 1.00
#: 1点の金額（円）。
STAKE = 100


class LocalBetRule:
    """当日の時点だけ、◎ の単勝（期待値 1.00 以上）と 複勝（期待値 1.25 以上の馬）を 1点 100円で買う。
    前日の時点（馬体重が届く前。オッズだけ）は買わない。"""

    def pick(self, table: pd.DataFrame, race_day: bool) -> LocalBets:
        if not race_day:
            return LocalBets((), ("馬体重が届く前の前日の時点では買わない",))
        win_lines, win_reason = self._win(table)
        place_lines, place_reason = self._place(table)
        lines = (*win_lines, *place_lines)
        return LocalBets(lines, () if lines else (win_reason, place_reason))

    @staticmethod
    def _win(table: pd.DataFrame) -> tuple[tuple[str, ...], str]:
        top = table[table[MARK] == TOP_MARK]
        if top.empty:
            return (), "◎ が無い"
        pick = top.iloc[0]
        if pick[WIN_VALUE] < WIN_VALUE_LINE:
            return (), f"◎ の単勝の期待値 {pick[WIN_VALUE]:.2f} は {WIN_VALUE_LINE:.2f} 未満"
        return (f"単勝 ◎{int(pick[HORSE_NO])} {pick[HORSE_NAME]}（期待値 {pick[WIN_VALUE]:.2f}）{STAKE}円",), ""

    @staticmethod
    def _place(table: pd.DataFrame) -> tuple[tuple[str, ...], str]:
        picks = table[table[PLACE_VALUE] >= PLACE_VALUE_LINE]
        lines = tuple(f"複勝 {int(row[HORSE_NO])} {row[HORSE_NAME]}（期待値 {row[PLACE_VALUE]:.2f}）{STAKE}円"
                      for _, row in picks.iterrows())
        return lines, "" if lines else f"複勝の期待値 {PLACE_VALUE_LINE:.2f} 以上の馬はいない"
