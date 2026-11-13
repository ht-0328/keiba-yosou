"""確かめに使った WIN5 の日と、除いた日・使った確率の内訳の表。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import pandas as pd

from 共通.render import Table

from yosou.shared.feature import PredictionTiming

from 印の成績.win5_backtest_day import Win5BacktestDay
from 印の成績.win5_backtest_days import ODDS_ONLY
from 印の成績.win5_periods import Win5Periods


class Win5CoverageReport:
    """期間ごとの、確かめに使った WIN5 の日数・キャリーオーバーの日数・除いた日数（理由ごと）と、対象レースで使った確率（当日・前日・
    オッズだけ）のレースの数（設計書「近走と適性からWIN5の買い目を決める」07 のまね方と 15 の 3 の扱いが、どれだけ効いたかを見る）。"""

    def table(self, days: Sequence[Win5BacktestDay], skipped: pd.DataFrame) -> Table:
        periods = Win5Periods()
        used: dict[str, list[Win5BacktestDay]] = {}
        for day in days:
            used.setdefault(str(periods.label_of(day.race_date)), []).append(day)
        names = list(dict.fromkeys([*used, *skipped["期間"].tolist()]))
        rows = [self._row(name, used.get(name, []), skipped.loc[skipped["期間"] == name]) for name in names]
        return Table(["期間", "確かめた日", "そのうちキャリーオーバーの日", "当日の予測のレース", "前日の予測のレース", "オッズだけのレース（障害）",
                      "最初の日", "最後の日", "除いた日", "除いた理由"], rows,
                     title="WIN5 の確かめに使った日",
                     note="1レース目の発走から 60分以上あとのレースは前日の予測（馬体重が出ていないとみなす）。区切りごとの予測が無い平地のレースが"
                          "ある日は、その日の期待値を出せないので、この予想も比べる相手も数えない。")

    def _row(self, name: str, days: list[Win5BacktestDay], skipped: pd.DataFrame) -> list[object]:
        sources = Counter(source for day in days for source in day.sources)
        reasons = "・".join(f"{reason} {count}日" for reason, count in skipped["理由"].value_counts().items())
        dates = [day.race_date for day in days]
        return [name, len(days), sum(day.carry > 0 for day in days), sources.get(PredictionTiming.RACE_DAY.label, 0),
                sources.get(PredictionTiming.DAY_BEFORE.label, 0), sources.get(ODDS_ONLY, 0), min(dates, default=""),
                max(dates, default=""), len(skipped), reasons]
