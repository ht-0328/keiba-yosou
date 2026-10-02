"""人気で決める買い目を、レースごとに馬番の組にして払戻と照らし、年ごとと全体の回収率にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from 決着の型.pattern_bet import PatternBet
from 決着の型.popularity_map import PopularityMap

#: 1点 100 円。
STAKE_YEN = 100
COLUMNS: tuple[str, ...] = ("開催年", "レース数", "買ったレース数", "点数", "購入額", "的中レース数", "的中率", "払戻", "回収率")
TOTAL_LABEL = "合計"


class PatternSettlement:
    """買い目（``PatternBet``）を 1点 100円で全レースに当てて精算する。

    買い目が1点も無いレース（その人気の馬がいない）は買わない。的中は、買い目の組と同じ組番の払戻を全部足す
    （ワイドの多重的中・同着の複数の組も足す）。
    """

    def __init__(self, bet: PatternBet) -> None:
        self._bet = bet

    def settle(self, races: pd.DataFrame, popularity: PopularityMap, payouts: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1レース: ``year``・``tickets``（点数）・``hit``・``yen``（払戻の合計）。"""
        paid = self._paid_by_race(payouts)
        rows = []
        for race_id, year in zip(races.index, races["year"]):
            tickets = self._bet.tickets(popularity.of(race_id))
            yen = sum(amount for combo, amount in paid.get(race_id, ()) if combo in tickets)
            rows.append((race_id, int(year), len(tickets), yen > 0, int(yen)))
        return pd.DataFrame(rows, columns=["race_id", "year", "tickets", "hit", "yen"])

    def table(self, settled: pd.DataFrame, condition: str) -> Table:
        """年ごとの行と合計の行。"""
        rows = [self._cells(str(year), group) for year, group in settled.groupby("year", sort=True)]
        rows.append(self._cells(TOTAL_LABEL, settled))
        table = Table(list(COLUMNS), rows, title=f"{self._bet.text} — {condition}",
                      note=f"{self._bet.kind.name}を 1点 100円。買い目の無いレース（その人気の馬がいない）は買わない。人気は確定の単勝人気。")
        table.meta = {"bet": self._bet.text, "races": int(len(settled)), "condition": condition}
        return table

    def _paid_by_race(self, payouts: pd.DataFrame) -> dict[str, list[tuple[tuple[int, ...], int]]]:
        paid: dict[str, list[tuple[tuple[int, ...], int]]] = {}
        for race_id, combo, yen in zip(payouts["race_id"], payouts["combo"], payouts["yen"]):
            paid.setdefault(race_id, []).append((self._bet.kind.canonical(tuple(combo)), int(yen)))
        return paid

    @staticmethod
    def _cells(label: str, settled: pd.DataFrame) -> list[str]:
        bought = settled[settled["tickets"].gt(0)]
        tickets = int(bought["tickets"].sum())
        stake = tickets * STAKE_YEN
        hits = int(bought["hit"].sum())
        yen = int(bought["yen"].sum())
        hit_rate = f"{hits / len(bought) * 100:.1f}%" if len(bought) else "—"
        recovery = f"{yen / stake * 100:.1f}%" if stake else "—"
        return [label, str(len(settled)), str(len(bought)), str(tickets), str(stake), str(hits), hit_rate, str(yen), recovery]
