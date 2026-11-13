"""段階の予算の候補の、期間ごとの成績の表。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_win5_tickets.payout import TICKET_YEN
from yosou.form_aptitude_win5_tickets.settlement import PERIOD, RACE_DATE, STAKE, STRATEGY

from 印の成績.win5_bet_columns import LARGE_DAY
from 印の成績.win5_periods import CONFIRM, EXPLORE
from 印の成績.win5_strategy_summary import Win5StrategySummary
from 印の成績.win5_summary_cells import HEADERS, Win5SummaryCells
from 印の成績.win5_tier_strategy import ADOPTED_TIER, TIER_CANDIDATES, TIER_JUDGE

#: 採用した決め方の印。
ADOPTED_MARK = "採用"
#: 表の見出し（成績のセルの前後に足す列）。
_LEAD = ("決め方", "期間", "多く買う日")
_TAIL = ("年あたりの金額（円）", "印")


class Win5TierReport:
    """設計書「近走と適性からWIN5の買い目を決める」16 の「段階の予算の確かめ」。候補（固定の一覧 ``TIER_CANDIDATES``）ごと・期間（探索・確認）ごとの、
    買った日数・多く買う日の数・投資・払戻・回収率・当たった回数・的中率・90% の幅・年あたりの金額（投資 ÷ その期間に買った年の数）。
    買う日はどの候補も判断用の買い目（``TIER_JUDGE``）で同じなので、買った日数は候補の間で同じになる。"""

    def __init__(self) -> None:
        self._summary = Win5StrategySummary()
        self._cells = Win5SummaryCells()

    def table(self, settled: pd.DataFrame) -> Table:
        """``settled`` は段階の予算の候補の精算の行（``Win5TierBets`` の行に期間の列を足したもの）。"""
        rows = []
        for strategy in TIER_CANDIDATES:
            for period in (EXPLORE, CONFIRM):
                group = settled.loc[(settled[STRATEGY] == strategy.label) & (settled[PERIOD] == period)]
                rows.append(self._row(strategy.rule_text, period, group, strategy is ADOPTED_TIER))
        note = (f"買う日は、どの決め方も判断用の買い目（{TIER_JUDGE.label}）の日の期待値が線以上の日。一律 {TIER_JUDGE.budget}点は"
                f"「この予想」の {TIER_JUDGE.label} と同じ買い目。年あたりの金額は、その期間に買った年の数で投資を割ったもの。"
                f"1点 {TICKET_YEN}円。確定オッズで確かめた値。")
        return Table([*_LEAD, *HEADERS, *_TAIL], rows, title="WIN5 の段階の予算の候補（探索期間と確認期間）", note=note)

    def _row(self, rule: str, period: str, group: pd.DataFrame, adopted: bool) -> list[object]:
        mark = ADOPTED_MARK if adopted else ""
        if group.empty:
            return [rule, period, 0, *self._cells.cells(None), 0, mark]
        summary = self._summary.of(group).iloc[0]
        years = group[RACE_DATE].astype(str).str[:4].nunique()
        per_year = int(round(int(group[STAKE].sum()) / years)) if years else 0
        return [rule, period, int(group[LARGE_DAY].astype(bool).sum()), *self._cells.cells(summary), per_year, mark]
