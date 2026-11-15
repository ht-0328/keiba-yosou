"""レースごとに、券種ごとの買い目の期待値が高い上位 k 券種を買う決まり（設計書 16 の 6.5 のア）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .shape_counter import MEAN_VALUE, POINTS, SHAPE

#: どのレースでも残す券種の数（全部の重賞を買う。設計書 16 の 6.1）。
MIN_TICKETS = 2


@dataclass(frozen=True)
class TopValueRule:
    """1つの重賞ごとに、券種ごとに選んだ形の買い目の期待値の平均（``mean_value``）が高い順に ``k`` 券種を買う。

    ``line`` を付けると、期待値が線に届かない券種を外す（外しても ``MIN_TICKETS`` 券種は残す）。買い目の無い券種（点数 0）は選ばない。
    """

    k: int
    line: float | None = None

    @property
    def name(self) -> str:
        return f"期待値の上位 {self.k} 券種" + (f"・期待値 {self.line:g} 未満は外す（2券種は残す）" if self.line is not None else "")

    def pick(self, counts: pd.DataFrame, chosen: dict[str, int]) -> pd.DataFrame:
        """``counts`` は ``ShapeCounter.count`` の表、``chosen`` は券種 → 形の番号。戻り値は買う行（1行 = 重賞 × 券種）と列 ticket。"""
        ticket_of = {shape: ticket for ticket, shape in chosen.items()}
        rows = counts[counts[SHAPE].isin(ticket_of) & (counts[POINTS] > 0)].assign(ticket=lambda frame: frame[SHAPE].map(ticket_of))
        ranked = rows.sort_values(["race_id", MEAN_VALUE], ascending=[True, False])
        ranked["order"] = ranked.groupby("race_id").cumcount()
        kept = ranked[ranked["order"] < self.k]
        if self.line is not None:
            kept = kept[(kept[MEAN_VALUE] >= self.line) | (kept["order"] < MIN_TICKETS)]
        return kept.drop(columns=["order"])
