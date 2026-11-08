"""過去の WIN5 での精算の結果を、買い方ごと・期間ごと・年ごとの成績の表にする。"""

from __future__ import annotations

import math

import pandas as pd

from 共通.bootstrap_interval import BootstrapInterval
from 共通.render import Table

#: 精算の結果の表（1行 = 1つの買い方の、買った1日）の列の名前。
STRATEGY = "買い方"
PERIOD = "期間"
RACE_DATE = "開催日"
STAKE = "投資"
PAYOUT = "払戻"
HIT = "当たり"
SETTLED_COLUMNS: tuple[str, ...] = (STRATEGY, PERIOD, RACE_DATE, STAKE, PAYOUT, HIT)
#: 表の見出し。
_HEADERS = ("買った日数", "投資", "払戻", "回収率", "的中率", "90%の幅")


class Win5BacktestTables:
    """買い方ごと・期間ごと（探索・確認）と、買い方ごと・年ごとの、買った日数・投資・払戻・回収率・的中率・90% の幅の表（設計書 16 の 2.）。

    90% の幅は、WIN5 の日を単位にしたブートストラップ（共通の ``BootstrapInterval``。手本の確かめと同じ出し方）。
    渡すのは買った日の行だけ（見送りの日は入れない）。数値は Git の対象外の ``reports/`` に出す（道具「印の成績」の ``--win5``）。
    """

    def __init__(self, interval: BootstrapInterval | None = None) -> None:
        self._interval = interval or BootstrapInterval()

    def tables(self, settled: pd.DataFrame) -> list[Table]:
        """``settled`` の列は ``SETTLED_COLUMNS``。"""
        by_year = settled.assign(**{PERIOD: settled[RACE_DATE].str[:4] + "年"})
        return [
            self._table(settled, "WIN5 の買い方ごと・期間ごとの成績"),
            self._table(by_year, "WIN5 の買い方ごと・年ごとの成績"),
        ]

    def _table(self, settled: pd.DataFrame, title: str) -> Table:
        rows = [self._row(strategy, period, group) for (strategy, period), group in settled.groupby([STRATEGY, PERIOD], sort=False)]
        return Table([STRATEGY, PERIOD, *_HEADERS], rows, title=title,
                     note="確定オッズで確かめた値。実際に買うとき（締め切り前のオッズ）より良く出ることがある。払戻には返還の代金を含む。")

    def _row(self, strategy: str, period: str, group: pd.DataFrame) -> list[object]:
        stake, payout = int(group[STAKE].sum()), int(group[PAYOUT].sum())
        low, high = self._interval.of(group[RACE_DATE], group[STAKE], group[PAYOUT])
        return [strategy, period, len(group), stake, payout, self._rate(payout, stake), self._rate(int(group[HIT].sum()), len(group)),
                self._range(low, high)]

    def _rate(self, numerator: float, denominator: float) -> str:
        return f"{numerator / denominator:.1%}" if denominator else ""

    def _range(self, low: float, high: float) -> str:
        if math.isnan(low) or math.isnan(high):
            return ""
        return f"{low:.1%}〜{high:.1%}"
