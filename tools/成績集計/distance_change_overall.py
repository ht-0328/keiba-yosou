"""目次に置く、全コースを合わせた距離の変更の傾向と、コースごとの差が年をまたいで続くかの表。"""

from __future__ import annotations

import pandas as pd

from 共通 import distance_change
from 共通.popularity_expectation import placed, won

#: 期間の区切り（開催年）。4年ずつ。
PERIODS: tuple[tuple[str, int, int], ...] = (
    ("2011〜2014年", 2011, 2014), ("2015〜2018年", 2015, 2018), ("2019〜2022年", 2019, 2022), ("2023年〜", 2023, 9999),
)
#: 前半と後半の境目（この年までが前半）。
HALF_LAST_YEAR = 2018
#: 続くかを見るときに、コースの短縮・延長それぞれに要る出走数（前半・後半とも）。
MIN_RUNS = 30
_UNIT = ["venue_code", "track_code", "distance"]
_SHOWN = (distance_change.SHORTER, distance_change.SAME, distance_change.LONGER)


class DistanceChangeOverall:
    """平地の出走（``ReferenceRuns`` と ``ReferenceLabels`` の表）から、全コースを合わせた傾向と、コースごとの差の続き方を数える。

    人気から見た差は、同じコース（競馬場・コース・距離）・同じ期間・同じ人気の馬の率との差。コースの違い（少頭数のコースなど）と
    人気の偏りを除いたうえで、全コースを合わせる。
    """

    def lines(self, runs: pd.DataFrame) -> list[str]:
        flat = self._scored(runs[runs["surface"].ne("障害") & runs["popularity"].notna()])
        return ["", "### 全コースを合わせた傾向（期間ごと）", "",
                "どの期間でも同じ向きなら、コースによらない傾向と読める。値は人気から見た差（pt）。", "",
                *self._overall_table(flat), "",
                "### コースごとの差は年をまたいで続くか", "",
                f"コースごとの「延長 − 短縮」の人気から見た差を、前半（〜{HALF_LAST_YEAR}年）と後半（{HALF_LAST_YEAR + 1}年〜）で"
                f"別々に数えて比べたもの（短縮・延長とも両方の期間で出走 {MIN_RUNS} 以上のコースだけ）。相関が 0 に近いか、"
                "向きが同じ割合が 5 割前後なら、コースごとの差は年をまたいで続いておらず、偶然の振れと読める。", "",
                *self._persistence_table(flat)]

    @staticmethod
    def _scored(runs: pd.DataFrame) -> pd.DataFrame:
        """出走に、期間・前半か・勝ちと3着以内（1.0 か 0.0）と、同じコース・同じ期間・同じ人気の率（期待）を付ける。"""
        year = runs["race_date"].str[:4].astype(int)
        period = pd.Series(pd.NA, index=runs.index, dtype="string")
        for name, first, last in PERIODS:
            period = period.mask(year.between(first, last), name)
        scored = runs.assign(period=period, early=year.le(HALF_LAST_YEAR), win=won(runs), top3=placed(runs))
        key = [*_UNIT, "popularity", "period"]
        return scored.assign(exp_win=scored.groupby(key)["win"].transform("mean"),
                             exp_top3=scored.groupby(key)["top3"].transform("mean"))

    @staticmethod
    def _overall_table(flat: pd.DataFrame) -> list[str]:
        longshot = flat["popularity"].ge(distance_change.LONGSHOT_MIN_POPULARITY)
        header = ["期間", *(f"{change}の勝率の差" for change in _SHOWN), *(f"{change}の穴馬の複勝率の差" for change in _SHOWN)]
        lines = ["| " + " | ".join(header) + " |", "|" + " :--- |" * len(header)]
        for name, _, _ in PERIODS:
            part = flat[flat["period"].eq(name)]
            wins = [_gap(part[part["label_distance_change"].eq(change)], "win") for change in _SHOWN]
            longshots = [_gap(part[part["label_distance_change"].eq(change) & longshot[part.index]], "top3") for change in _SHOWN]
            lines.append(f"| {name} | " + " | ".join(wins + longshots) + " |")
        return lines

    def _persistence_table(self, flat: pd.DataFrame) -> list[str]:
        lines = ["| 見るもの | 比べたコースの数 | 前半と後半の相関 | 向きが同じ割合 |", "| :--- | :--- | :--- | :--- |"]
        longshots = flat[flat["popularity"].ge(distance_change.LONGSHOT_MIN_POPULARITY)]
        for name, rows, column in (("勝つ（勝率）", flat, "win"), ("穴馬の好走（複勝率）", longshots, "top3")):
            halves = pd.concat({half: self._course_spread(rows[rows["early"].eq(early)], column)
                                for half, early in (("前半", True), ("後半", False))}, axis=1).dropna()
            if len(halves) < 3:
                lines.append(f"| {name} | {len(halves)} | - | - |")
                continue
            same = (halves["前半"].gt(0) == halves["後半"].gt(0)).mean()
            lines.append(f"| {name} | {len(halves)} | {halves['前半'].corr(halves['後半']):+.2f} | {same * 100:.0f}% |")
        return lines

    @staticmethod
    def _course_spread(rows: pd.DataFrame, column: str) -> pd.Series:
        """コースごとの「延長の人気から見た差 − 短縮の人気から見た差」。短縮・延長のどちらかの出走が少ないコースは入れない。"""
        diff = rows[column] - rows[f"exp_{column}"]
        table = diff.groupby([*(rows[key] for key in _UNIT), rows["label_distance_change"]], observed=True).agg(["mean", "size"])
        table = table.unstack("label_distance_change")
        shorter, longer = distance_change.SHORTER, distance_change.LONGER
        if ("size", shorter) not in table.columns or ("size", longer) not in table.columns:
            return pd.Series(dtype=float)
        enough = table[("size", shorter)].ge(MIN_RUNS) & table[("size", longer)].ge(MIN_RUNS)
        return (table[("mean", longer)] - table[("mean", shorter)])[enough]


def _gap(rows: pd.DataFrame, column: str) -> str:
    if rows.empty:
        return "-"
    return f"{(rows[column] - rows[f'exp_{column}']).mean() * 100:+.2f}pt"
