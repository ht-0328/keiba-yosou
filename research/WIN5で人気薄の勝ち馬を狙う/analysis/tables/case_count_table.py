"""事例の数の表: WIN5 の対象レースと平地の全レースで、人気薄が勝ったレースの数と、WIN5 の日ごとの人気薄の勝ちの数。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent


@dataclass(frozen=True)
class CaseCountTable:
    """``races`` は ``RaceTable`` の表（全平地のレース）。"""

    longshot_from: int = 10

    def build(self, races: pd.DataFrame) -> list[Table]:
        win5 = races.loc[races["win5_leg"].notna()]
        rows = [self._row("平地の全レース", races), self._row("WIN5 の対象レース", win5)]
        counts = Table(["範囲", "レース数", f"{self.longshot_from}番人気以下が勝った", "割合", "市場が見た数（オッズから見た勝率の合計）"],
                       rows, title="1. 事例の数",
                       note="市場が見た数は、各レースの10番人気以下のオッズから見た勝率の合計を足したもの（市場の見立てどおりなら、この数だけ起きる）。")
        per_day = win5.groupby("race_date")["longshot_won"].sum().astype(int).value_counts().sort_index()
        days = len(win5["race_date"].unique())
        day_rows = [[f"{count}レース", int(n), percent(n, days)] for count, n in per_day.items()]
        by_day = Table(["その日の5レースのうち人気薄が勝った数", "日数", "割合"], day_rows,
                       title=f"2. WIN5 の日ごとの、{self.longshot_from}番人気以下が勝ったレースの数（全 {days}日）")
        return [counts, by_day]

    @staticmethod
    def _row(label: str, races: pd.DataFrame) -> list[object]:
        won = int(races["longshot_won"].sum())
        return [label, len(races), won, percent(won, len(races)), f"{races['longshot_market'].sum():.1f}"]
