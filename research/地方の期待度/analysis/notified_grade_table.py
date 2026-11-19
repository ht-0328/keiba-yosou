"""通知のときの推奨買目（払戻つき）を1レースにまとめ、期待の儲けの等級ごと・点数の高低ごとの成績の表にする。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.race_grade import GRADES, LocalBetProfitScale

from 共通.perf import percent
from 共通.render import Table

from .race_scores import EXPECTED_PROFIT, RaceScores

HEADERS: tuple[str, ...] = ("分け方", "区分", "レース数", "割合", "1レースの点数", "回収率", "的中レース率", "1レースの儲け（円）")
#: 点数の高低で分ける数（等しい頭数の組）。
BANDS = 5
_GRADE, _BAND, _HIT = "grade", "band", "hit"


class NotifiedGradeTable:
    """``bets`` は1行 = 1点（``race_id``・``race_date``・期待値・``payout``（100円あたり。外れは 0））。
    行は 全体、期待の儲けの等級（``LocalBetProfitScale`` の S・A・B・C）、点数の低い順の ``BANDS`` 組。
    等級が高い・点数が高い組ほど回収率が高ければ、その点数は通知のときの目安として使える。"""

    def races(self, bets: pd.DataFrame) -> pd.DataFrame:
        scored = RaceScores().of(bets.assign(year=pd.to_datetime(bets["race_date"]).dt.year))
        hit = bets.groupby("race_id")["payout"].max().gt(0).rename(_HIT)
        scored = scored.merge(hit, left_on="race_id", right_index=True)
        ranks = scored[EXPECTED_PROFIT].rank(method="first")
        return scored.assign(**{_GRADE: scored[EXPECTED_PROFIT].map(LocalBetProfitScale().of),
                                _BAND: pd.qcut(ranks, min(BANDS, len(scored)), labels=False) + 1})

    def table(self, bets: pd.DataFrame, title: str, note: str = "") -> Table:
        races = self.races(bets)
        rows = [self._row("全体", "全体", races, len(races))]
        rows += [self._row("期待の儲けの等級", grade, races[races[_GRADE] == grade], len(races)) for grade in GRADES]
        rows += [self._row("点数の低い順の組", f"{band}（{part[EXPECTED_PROFIT].min():.2f}〜{part[EXPECTED_PROFIT].max():.2f}）", part, len(races))
                 for band, part in races.groupby(_BAND)]
        return Table(list(HEADERS), rows, title=title, note=note)

    @staticmethod
    def _row(kind: str, label: str, part: pd.DataFrame, total: int) -> list:
        if part.empty:
            return [kind, label, 0, "—", "—", "—", "—", "—"]
        stake, returned = float(part["stake"].sum()), float(part["returned"].sum())
        return [kind, label, len(part), percent(len(part) / total), f"{part['points'].mean():.1f}", percent(returned / stake),
                percent(float(part[_HIT].mean())), f"{(returned - stake) / len(part):,.0f}"]
