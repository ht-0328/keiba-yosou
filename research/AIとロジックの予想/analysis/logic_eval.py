"""研究「AIとロジックの予想」: AI だけの予想（今の本番）と、ロジックで直した予想を、本番と同じ配り方で比べる部品。

``Period`` は1つの期間の買い目の候補（表と裏）と、レースごとの材料（AI の印の材料と、``logic_features.py`` のロジックの材料）を持つ。
``evaluate`` に「レースを買うか」と「どの組を候補にするか」の決まりを渡すと、買ったレースの割合・回収率・的中率・1日の儲けを返す。
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import race_outcomes as outcomes  # noqa: E402

OUT = outcomes.OUT

#: レースの材料（1行 = 1レース）を受け取り、そのレースを買う候補にするか。
RaceRule = Callable[[pd.Series], bool]
#: 1レースの候補の組（表と裏）とレースの材料を受け取り、配る組の表を返す。
TicketRule = Callable[[pd.DataFrame, pd.Series], pd.DataFrame]


def front_and_back(race: pd.DataFrame, info: pd.Series) -> pd.DataFrame:
    """今の本番の組（表と、裏の確率が線以上なら馬単の裏）。"""
    add = info["p"] >= outcomes.REVERSE_LINE
    return race[(race["kind"] == "表") | ((race["kind"] == outcomes.compare.EXACTA_BACK) & add)]


def every_race(info: pd.Series) -> bool:
    return True


@dataclass
class Period:
    name: str
    pool: pd.DataFrame
    races: pd.DataFrame

    @classmethod
    def load(cls, name: str, learn_until: str, start: str, end: str) -> "Period":
        pool = outcomes.pool(learn_until, start, end)
        races = pd.read_pickle(OUT / f"races_{start}_{end}.pkl")
        races = races[races["race_id"].isin(set(pool["race_id"]))].set_index("race_id")
        races["p"] = pool.drop_duplicates("race_id").set_index("race_id")["p"]
        return cls(name, pool, races)

    def evaluate(self, race_rule: RaceRule = every_race, ticket_rule: TicketRule = front_and_back) -> dict:
        stakes = outcomes.EqualPayoutStakes()
        rows = []
        for race_id, race in self.pool.groupby("race_id", sort=False):
            info = self.races.loc[race_id]
            if not race_rule(info):
                continue
            tickets = ticket_rule(race, info).to_dict("records")
            chosen, _ = stakes.allocate(tickets)
            expected = sum(share * ticket["value"] for ticket, share in chosen if ticket["value"] == ticket["value"]) if chosen else 0.0
            if not chosen or expected < outcomes.BUY_LINE:
                continue
            yen = outcomes.mark_return._amounts(chosen)
            rows.append((race_id, sum(yen), sum(amount * ticket["pay"] / 100 for amount, (ticket, _) in zip(yen, chosen, strict=True))))
        bought = pd.DataFrame(rows, columns=["race_id", "stake", "back"])
        races, days = self.pool["race_id"].nunique(), self.pool["day"].nunique()
        paid, back = bought["stake"].sum(), bought["back"].sum()
        return {"期間": self.name, "買う": len(bought), "買う割合": len(bought) / races, "回収率": back / paid if paid else float("nan"),
                "的中率": (bought["back"] > 0).mean() if len(bought) else float("nan"), "1日の儲け": (back - paid) / days}
