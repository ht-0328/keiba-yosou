"""その日の WIN5 の発売票数を、それより前の回から見積もる。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..repository.win5_columns import RACE_DATE, SATURDAY, VOTES

#: 見積もりに使う直近の回の数。
RECENT_COUNT = 10


class PoolSizeEstimate:
    """その日より前の WIN5 のうち、同じ曜日の種類（土曜か、それ以外）の直近 10回の発売票数の中央値（設計書 09 の 2.）。

    その日の確定の発売票数は締め切りまで分からないので使わない（設計書 11 の 8）。同じ曜日の種類の回が1つも無ければ、
    曜日を問わず直近 10回の中央値にする。過去の WIN5 は ``Win5HistoryRepository`` の表（1行 = 1回の当たり組）。
    """

    def of(self, history: pd.DataFrame, race_date: date, is_saturday: bool) -> float:
        """発売票数の見積もり。その日より前の回が無ければ ``LookupError``。"""
        earlier = history.loc[history[RACE_DATE] < race_date.isoformat(), [RACE_DATE, SATURDAY, VOTES]]
        days = earlier.drop_duplicates(RACE_DATE).dropna(subset=[VOTES]).sort_values(RACE_DATE)
        same_kind = days.loc[days[SATURDAY] == is_saturday]
        chosen = same_kind if not same_kind.empty else days
        if chosen.empty:
            raise LookupError(f"{race_date.isoformat()} より前の WIN5 が無いので、発売票数を見積もれません")
        return float(chosen[VOTES].tail(RECENT_COUNT).median())
