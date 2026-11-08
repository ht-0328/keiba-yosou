"""抑えの買い目の候補（線 × 組み方）を作って精算し、探索の期間の回収率で1つ選ぶ。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .evaluation_frame import EXPLORE
from .hedge_tickets import SHAPES, HedgeTickets

#: 2頭以上の確率の上位何割のレースで買うか（線は探索の期間の割合で決める）。
SHARES: tuple[float, ...] = (0.1, 0.2, 0.3)
#: 選ぶときに要る、探索の期間の当たったレースの数の下限（1回の大当たりで決まらないように）。
MIN_HITS = 20


@dataclass(frozen=True)
class HedgeStudy:
    """``races`` は ``PairProbability.races`` のレースの表、``settlement`` は ``HedgeSettlement``。
    ``run`` は（候補の名前 → 払戻を付けた買い目）と、選んだ候補の名前を返す。選び方: 探索の期間で当たったレースが 20 以上の候補のうち、
    探索の期間の回収率がいちばん高いもの。"""

    races: pd.DataFrame
    settlement: object

    def run(self, favorites: pd.Series, popular: pd.Series, main: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], str]:
        explore = self.races.loc[self.races["period"] == EXPLORE, "two_or_more"]
        candidates = {}
        for share in SHARES:
            line = float(explore.quantile(1 - share))
            chosen = self.races.loc[self.races["two_or_more"] >= line]
            for shape in SHAPES:
                tickets = HedgeTickets(shape).build(chosen, favorites, popular, main)
                candidates[f"{shape}・上位{int(share * 100)}%（線 {line:.3f}）"] = self.settlement.settle(tickets)
        return candidates, self._choose(candidates)

    @staticmethod
    def _choose(candidates: dict[str, pd.DataFrame]) -> str:
        scores = {}
        for name, tickets in candidates.items():
            part = tickets.loc[tickets["period"] == EXPLORE]
            if part.empty or part.loc[part["payout"] > 0, "race_id"].nunique() < MIN_HITS:
                continue
            scores[name] = part["payout"].sum() / (100 * len(part))
        return max(scores, key=scores.get) if scores else next(iter(candidates))
