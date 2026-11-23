"""成績の表（1頭1行）を、期間ごとの回収率の表にまとめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 共通.render import Table

#: まとめの表の列。
HEADERS: tuple[str, ...] = ("期間", "券種", "買った回数", "点数", "的中", "的中率", "買った額", "戻った額", "回収率", "払戻の上位5本を除いた回収率")
#: 券種 → (買った額の列, 戻った額の列)。
TICKETS: dict[str, tuple[str, str]] = {"単勝": ("win_cost", "win_back"), "馬単（1着固定）": ("exacta_cost", "exacta_back"),
                                        "3連単（1着固定）": ("trifecta_cost", "trifecta_back")}
#: 高い払戻に頼っていないかを見るために除く本数。
TOP = 5
STAKE = 100


class LateSummary:
    """期間は 全体・年・四半期。回収率は 戻った額 ÷ 買った額。「上位5本を除いた回収率」は、戻った額の大きい5回ぶんを 0 円にした回収率
    （少ない高配当に頼っているほど、ここが下がる）。"""

    def table(self, settled: pd.DataFrame, title: str, note: str = "") -> Table:
        rows: list[tuple] = []
        periods = [("全体", settled)]
        periods += [(f"{year}年", part) for year, part in settled.groupby(settled["day"].dt.year)]
        periods += [(str(quarter), part) for quarter, part in settled.groupby(settled["day"].dt.to_period("Q"))]
        for label, part in periods:
            rows += [self._row(label, ticket, part[cost], part[back]) for ticket, (cost, back) in TICKETS.items()]
        return Table(list(HEADERS), [list(row) for row in rows], title=title, note=note)

    @staticmethod
    def _row(label: str, ticket: str, cost: pd.Series, back: pd.Series) -> tuple:
        paid = float(cost.sum())
        returned = float(back.sum())
        top = float(np.sort(back.to_numpy())[::-1][:TOP].sum())
        rate = f"{returned / paid:.1%}" if paid else "—"
        trimmed = f"{(returned - top) / paid:.1%}" if paid else "—"
        hits = int((back > 0).sum())
        return (label, ticket, len(cost), int(paid // STAKE), hits, f"{hits / len(cost):.1%}" if len(cost) else "—",
                f"{paid:,.0f}", f"{returned:,.0f}", rate, trimmed)
