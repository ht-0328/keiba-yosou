"""公開ルール（◎ の単勝）の成績の表（期間ごと・年ごと・線を動かしたとき）を作る。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import pandas as pd

from 共通.render import Table

from 的中実績の公開ルール.analysis.day_bootstrap import LOW_PERCENTILE, DayBootstrap
from 的中実績の公開ルール.analysis.top_picks import TopPicks

#: 探す期間の最後の年（これより後が確かめる期間）。
SEARCH_LAST_YEAR = 2022
#: 線を動かす表の、期待値の線と単勝オッズの上限。
VALUE_LINES = (0.95, 0.975, 1.0, 1.025, 1.05, 1.1)
ODDS_CAPS = (5.0, 5.5, 6.0, 6.5, 7.0, 8.0)


@dataclass(frozen=True)
class RuleReport:
    """``final`` は確定オッズで選んだ ◎ の行（``TopPicks.of``。全期間）、``snapshot`` は締め切り前のオッズで選んだ ◎ の行（時系列オッズのある約1年）。
    どちらも1行 = 1レース・100円で、払戻は確定の払戻。``value_line``・``odds_cap`` が公開ルールの線。"""

    final: pd.DataFrame
    snapshot: pd.DataFrame
    value_line: float
    odds_cap: float
    snapshot_label: str = "10分前のオッズ"

    def tables(self) -> list[Table]:
        return [self.periods(), self.years(), self.lines()]

    def periods(self) -> Table:
        """期間ごと（探す・確かめる・全期間は確定オッズで選んだもの、最後の行は締め切り前のオッズで選んだもの）。"""
        parts = [("確定オッズ・探す期間", self._search(self.final)), ("確定オッズ・確かめる期間", self._check(self.final)),
                 ("確定オッズ・全期間", self.final), (self.snapshot_label, self.snapshot)]
        rows = [[name, *_summary(TopPicks.bought(part, self.value_line, self.odds_cap))] for name, part in parts]
        columns = ["期間", "開催日", "買ったレース", "1開催日の平均", "当たったレース", "的中率", "回収率", f"運が悪いと（下から {LOW_PERCENTILE:g}%）", "最長の外れ続き"]
        return Table(columns, rows, title=f"期間ごと（◎ の単勝の期待値 {self.value_line:.2f} 以上・単勝 {self.odds_cap:g}倍以下）",
                     note="運が悪いと = 開催日を引き直したときの回収率の下の端。払戻はどれも確定の払戻")

    def years(self) -> Table:
        bought = TopPicks.bought(self.final, self.value_line, self.odds_cap)
        rows = [[year, *_summary(part)[1:6]] for year, part in bought.groupby("year")]
        return Table(["年", "買ったレース", "1開催日の平均", "当たったレース", "的中率", "回収率"], rows, title="年ごと（確定オッズで選んだもの）")

    def lines(self) -> Table:
        """期待値の線と単勝オッズの上限を動かしたときの回収率と的中率。"""
        parts = (self._search(self.final), self._check(self.final), self.snapshot)
        rows = [[f"{value:.3f}", f"{cap:g}", *(_rate_and_hit(TopPicks.bought(part, value, cap)) for part in parts)]
                for value, cap in product(VALUE_LINES, ODDS_CAPS)]
        return Table(["期待値の線", "単勝の上限", "探す期間", "確かめる期間", self.snapshot_label], rows,
                     title="線を動かしたとき（回収率・的中率）", note="公開ルールの線だけが良く、周りが崩れていないかを見る")

    @staticmethod
    def _search(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[frame["year"] <= SEARCH_LAST_YEAR]

    @staticmethod
    def _check(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[frame["year"] > SEARCH_LAST_YEAR]


def _summary(bought: pd.DataFrame) -> list:
    """開催日・買ったレース・1開催日の平均・当たったレース・的中率・回収率・運が悪いと・最長の外れ続き。"""
    if bought.empty:
        return [0, 0, "-", 0, "-", "-", "-", "-"]
    days = bought["day"].nunique()
    hits = int((bought["win_pay"] > 0).sum())
    return [days, len(bought), f"{len(bought) / days:.1f}", hits, f"{hits / len(bought):.1%}", f"{bought['win_pay'].sum() / len(bought):.1f}%",
            f"{DayBootstrap().low(bought):.1f}%", _longest_miss(bought)]


def _rate_and_hit(bought: pd.DataFrame) -> str:
    if bought.empty:
        return "-"
    return f"{bought['win_pay'].sum() / len(bought):.1f}%（{(bought['win_pay'] > 0).mean():.0%}）"


def _longest_miss(bought: pd.DataFrame) -> int:
    """開催日・レースの順に並べたときの、いちばん長い外れ続きのレース数。"""
    hits = (bought.sort_values(["day", "race_id"])["win_pay"] > 0).to_numpy()
    longest = run = 0
    for hit in hits:
        run = 0 if hit else run + 1
        longest = max(longest, run)
    return longest
