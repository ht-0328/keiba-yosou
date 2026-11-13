"""買い方ごとの成績（``Win5StrategySummary`` の1行）を、表のセルの文字にする。"""

from __future__ import annotations

import math

import pandas as pd

from yosou.form_aptitude_win5_tickets.settlement import PAYOUT, STAKE

from 印の成績.win5_strategy_summary import DAYS, HIGH, HIT_RATE, HITS, LOW, RECOVERY

#: セルの見出し（``cells`` の並び）。
HEADERS: tuple[str, ...] = ("買った日数", "投資", "払戻", "回収率", "当たった回数", "的中率", "90%の幅")


class Win5SummaryCells:
    """成績の1行を、買った日数・投資・払戻・回収率・当たった回数・的中率・90% の幅のセルにする（WIN5 の表で同じ見せ方にする）。"""

    def cells(self, row: pd.Series | None) -> list[object]:
        """``row`` が None（その期間に買った日が無い）なら、買った日数 0 と空のセル。"""
        if row is None:
            return [0, 0, 0, "", 0, "", ""]
        return [int(row[DAYS]), int(row[STAKE]), int(row[PAYOUT]), self._percent(row[RECOVERY]), int(row[HITS]),
                self._percent(row[HIT_RATE]), self._range(row[LOW], row[HIGH])]

    def _percent(self, value: float) -> str:
        return "" if pd.isna(value) else f"{float(value):.1%}"

    def _range(self, low: float, high: float) -> str:
        if math.isnan(float(low)) or math.isnan(float(high)):
            return ""
        return f"{float(low):.1%}〜{float(high):.1%}"
