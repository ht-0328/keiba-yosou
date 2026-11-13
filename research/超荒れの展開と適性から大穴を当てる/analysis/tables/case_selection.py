"""1レースずつ見る事例を、年・競馬場・芝ダが偏らないように選ぶ（ハンデ戦は決めた数を先に選ぶ）。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

#: 偏らないようにそろえる列。
_BALANCE: tuple[str, ...] = ("year", "venue", "surface")


@dataclass(frozen=True)
class CaseSelection:
    """``races``（``RaceTable``）のうち決着が ``outcome`` のレースから ``count`` 件選ぶ。そのうち ``handicap_count`` 件はハンデ戦。

    選び方: 候補を乱数（``seed``）で並べ替え、「すでに選んだ事例に同じ年・同じ競馬場・同じ芝ダが何件あるか」の合計がいちばん小さい
    レースを1件ずつ選ぶ。ハンデ戦を先に選び、残りをハンデ戦以外から選ぶ。返すのは選んだ race_id（選んだ順）。
    """

    seed: int = 20261109

    def pick(self, races: pd.DataFrame, outcome: str, count: int, handicap_count: int) -> list[str]:
        pool = races.loc[races["outcome"] == outcome]
        order = np.random.default_rng(self.seed).permutation(len(pool))
        pool = pool.iloc[order]
        chosen: list[str] = []
        counts: Counter = Counter()
        handicap = pool.loc[pool["handicap"] == "ハンデ戦"]
        others = pool.loc[pool["handicap"] != "ハンデ戦"]
        self._greedy(handicap, min(handicap_count, len(handicap)), chosen, counts)
        self._greedy(others, count - len(chosen), chosen, counts)
        return chosen

    @staticmethod
    def _greedy(pool: pd.DataFrame, count: int, chosen: list[str], counts: Counter) -> None:
        remaining = pool
        for _ in range(max(count, 0)):
            if remaining.empty:
                return
            score = sum(remaining[column].map(lambda value, c=column: counts[(c, value)]) for column in _BALANCE)
            best = score.idxmin()
            chosen.append(str(best))
            for column in _BALANCE:
                counts[(column, remaining.at[best, column])] += 1
            remaining = remaining.drop(index=best)
