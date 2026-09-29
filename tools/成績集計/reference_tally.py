"""出走の表を切り口の値ごとに分けて、成績7つの行（ページの表の1行）にする。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

#: 払戻は100円あたりの円。回収率の分母に使う。
STAKE_YEN = 100
#: ページの表の列（切り口の列のあと）。答え合わせ（``check.py``）はこの並びで読む。
PERF_HEADER: tuple[str, ...] = ("出走数", "着別度数", "勝率", "連対率", "複勝率", "馬券外率", "単勝回収率", "複勝回収率")
#: 勝率で並べるときの同点の決め方（勝率 → 連対率 → 複勝率 → 出走数、どれも大きい順）。
_RANK_ORDER: tuple[str, ...] = ("win_rate", "top2_rate", "top3_rate", "runs")
#: 値ごとに足し合わせる列（1着・2着・3着の数と、単勝・複勝の払戻）。
_SUMMED: tuple[str, ...] = ("first", "second", "third", "win_yen", "place_yen")


class ReferenceTally:
    """``ReferenceRuns`` の表を数える。値の順に全部並べる ``rows`` と、勝率の上位だけ出す ``top_rows`` がある。

    ``columns`` で分け、``shown`` 番目の列だけを表に出す（馬は血統登録番号で分けて馬名を出す）。値が空の出走は数えない。
    """

    def rows(self, runs: pd.DataFrame, columns: Sequence[str], shown: Sequence[int]) -> list[list[str]]:
        counted = self._count(runs, columns)
        return [self._cells(labels, shown, row) for labels, row in counted.iterrows()]

    def top_rows(self, runs: pd.DataFrame, columns: Sequence[str], shown: Sequence[int], *, top: int,
                 min_runs: int) -> list[list[str]]:
        """出走が ``min_runs`` 以上の値のうち、勝率の高い ``top`` 件（同点は連対率 → 複勝率 → 出走数）。"""
        counted = self._count(runs, columns)
        counted = counted[counted["runs"].ge(min_runs)]
        ranked = counted.assign(
            win_rate=counted["first"] / counted["runs"],
            top2_rate=(counted["first"] + counted["second"]) / counted["runs"],
            top3_rate=(counted["first"] + counted["second"] + counted["third"]) / counted["runs"],
        ).sort_values(list(_RANK_ORDER), ascending=False, kind="stable")
        return [self._cells(labels, shown, row) for labels, row in ranked.head(top).iterrows()]

    @staticmethod
    def _count(runs: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
        valued = runs.dropna(subset=list(columns))
        groups = valued.groupby(list(columns), observed=True, sort=True)
        return groups[list(_SUMMED)].sum().assign(runs=groups.size())

    @staticmethod
    def _cells(labels, shown: Sequence[int], row: pd.Series) -> list[str]:
        values = labels if isinstance(labels, tuple) else (labels,)
        runs, first, second, third = int(row["runs"]), int(row["first"]), int(row["second"]), int(row["third"])
        out = runs - first - second - third
        rates = (first / runs, (first + second) / runs, (first + second + third) / runs, out / runs,
                 int(row["win_yen"]) / (runs * STAKE_YEN), int(row["place_yen"]) / (runs * STAKE_YEN))
        return [*(label_text(values[index]) for index in shown), str(runs), f"{first}-{second}-{third}-{out}",
                *(f"{rate * 100:.1f}%" for rate in rates)]


def label_text(value) -> str:
    """表の先頭のセル。整数に見える数は整数で書く（``1.0`` ではなく ``1``）。"""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
