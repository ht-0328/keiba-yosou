"""探索期間の成績から、決まりどおりに買い方を1つ選ぶ。"""

from __future__ import annotations

import pandas as pd

from yosou.form_aptitude_win5_tickets.settlement import STRATEGY

from 印の成績.win5_strategy_summary import DAYS, HIT_RATE, RECOVERY

#: 選ぶ候補に残す、買った日数の下限（数日の大当たりで選ばないため）。
MIN_DAYS = 30
#: 探索期間で、これを超える回収率の買い方が無ければ「選べる買い方なし」。
BREAK_EVEN = 1.0


class Win5StrategyChoice:
    """設計書「近走と適性からWIN5の買い目を決める」16 の 4. の「探索期間で1つ選ぶ決まり」（結果を見る前に固定したもの）。

    1. 買った日が 30日以上の買い方だけを残す。2. 回収率がいちばん高いものを選ぶ（同じなら的中率の高いほう）。
    3. その回収率が 100% を超えなければ「選べる買い方なし」。
    """

    def best(self, summary: pd.DataFrame) -> str | None:
        """30日以上の買い方のうち、回収率（同じなら的中率）がいちばん高い買い方の名前。候補が無ければ None。"""
        candidates = summary.loc[summary[DAYS] >= MIN_DAYS]
        if candidates.empty:
            return None
        ranked = candidates.sort_values([RECOVERY, HIT_RATE], ascending=False, kind="stable")
        return str(ranked[STRATEGY].iloc[0])

    def choose(self, summary: pd.DataFrame) -> str | None:
        """決まりで選んだ買い方の名前。回収率が 100% を超えるものが無ければ None（選べる買い方なし）。"""
        best = self.best(summary)
        if best is None:
            return None
        recovery = float(summary.loc[summary[STRATEGY] == best, RECOVERY].iloc[0])
        return best if recovery > BREAK_EVEN else None
