"""切り口ごとに、3着以内率・1着率と、その人気から見た差（同じ重量種別・頭数の帯・人気の馬がふつう出す率との差）を並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

from .cells import percent, points

_NOTE = ("人気から見た差 = 実際の率 − 同じ重量種別・同じ頭数の帯（〜12・13〜15・16〜18頭）・同じ単勝人気の馬が 2015年からの平地でふつう出す率（ポイント）。"
         "± は標準誤差（各馬の期待の率で当たり外れが決まるとしたときのばらつき）。差が標準誤差の2倍を超えれば、偶然では説明しにくい。"
         "プラスなら市場（人気）がその切り口を見落として低く見ている。")


@dataclass(frozen=True)
class GapTable:
    """``runs``（``RunnerCuts`` の列を持つ出走の表）を ``cuts``（列名の並び）で分ける。``min_runs`` 未満の組は出さない。"""

    def build(self, runs: pd.DataFrame, cuts: list[str], title: str, min_runs: int = 30) -> Table:
        rows = []
        for values, part in runs.groupby(cuts, observed=True, sort=True):
            if len(part) < min_runs:
                continue
            labels = list(values) if isinstance(values, tuple) else [values]
            rows.append([*[str(label) for label in labels], *self._cells(part)])
        columns = [*cuts, "頭数", "3着以内率", "人気から見た差（3着以内）", "1着率", "人気から見た差（1着）"]
        return Table(columns, rows, title=title, note=_NOTE)

    @staticmethod
    def _cells(part: pd.DataFrame) -> list[object]:
        n = len(part)
        top3_error = float(np.sqrt((part["expected_top3"] * (1 - part["expected_top3"])).sum()) / n)
        win_error = float(np.sqrt((part["expected_win"] * (1 - part["expected_win"])).sum()) / n)
        top3_gap = float(part["top3"].mean() - part["expected_top3"].mean())
        win_gap = float(part["won"].mean() - part["expected_win"].mean())
        return [n, percent(part["top3"].sum(), n), points(top3_gap, top3_error), percent(part["won"].sum(), n, 2),
                points(win_gap, win_error)]
