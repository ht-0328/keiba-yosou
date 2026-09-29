"""出走の表を切り口の値ごとに分けて、成績7つの行（ページの表の1行）にする。"""

from __future__ import annotations

import pandas as pd

#: 払戻は100円あたりの円。回収率の分母に使う。
STAKE_YEN = 100
#: ページの表の列（切り口の列のあと）。答え合わせ（``check.py``）はこの並びで読む。
PERF_HEADER: tuple[str, ...] = ("出走数", "着別度数", "勝率", "連対率", "複勝率", "馬券外率", "単勝回収率", "複勝回収率")
#: 勝率で並べるときの同点の決め方（勝率 → 連対率 → 複勝率 → 出走数、どれも大きい順）。
_RANK_ORDER: tuple[str, ...] = ("win_rate", "top2_rate", "top3_rate", "runs")


class ReferenceTally:
    """``ReferenceRuns`` の表を数える。値の順に全部並べる ``rows`` と、勝率の上位だけ出す ``top_rows`` がある。"""

    def rows(self, runs: pd.DataFrame, column: str) -> list[list[str]]:
        """``column`` の値ごとの成績。値の小さい順（値が無い出走は数えない）。"""
        counted = self._count(runs, column)
        return [self._cells(label, row) for label, row in counted.sort_index().iterrows()]

    def top_rows(self, runs: pd.DataFrame, column: str, *, top: int, min_runs: int) -> list[list[str]]:
        """``column`` の値ごとの成績のうち、出走が ``min_runs`` 以上で勝率の高い ``top`` 件。"""
        counted = self._count(runs, column)
        counted = counted[counted["runs"].ge(min_runs)]
        ranked = counted.assign(
            win_rate=counted["first"] / counted["runs"],
            top2_rate=(counted["first"] + counted["second"]) / counted["runs"],
            top3_rate=(counted["first"] + counted["second"] + counted["third"]) / counted["runs"],
        ).sort_values(list(_RANK_ORDER), ascending=False, kind="stable")
        return [self._cells(label, row) for label, row in ranked.head(top).iterrows()]

    @staticmethod
    def _count(runs: pd.DataFrame, column: str) -> pd.DataFrame:
        valued = runs[runs[column].notna() & runs[column].astype(str).str.strip().ne("")]
        return valued.groupby(column, observed=True).agg(
            runs=("rid", "size"), first=("first", "sum"), second=("second", "sum"), third=("third", "sum"),
            win_yen=("win_yen", "sum"), place_yen=("place_yen", "sum"),
        )

    @staticmethod
    def _cells(label, row: pd.Series) -> list[str]:
        runs, first, second, third = int(row["runs"]), int(row["first"]), int(row["second"]), int(row["third"])
        out = runs - first - second - third
        rates = (first / runs, (first + second) / runs, (first + second + third) / runs, out / runs,
                 int(row["win_yen"]) / (runs * STAKE_YEN), int(row["place_yen"]) / (runs * STAKE_YEN))
        return [_label(label), str(runs), f"{first}-{second}-{third}-{out}", *(f"{rate * 100:.1f}%" for rate in rates)]


def _label(value) -> str:
    """表の先頭のセル。整数に見える数は整数で書く（``1.0`` ではなく ``1``）。"""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
