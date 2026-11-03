"""馬の集まり3つから1頭ずつ選んで組む3連複のルール（買うレースを荒れ具合で選べ、安い組を外せる）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.betting import TicketType

from 今週の予想.horse_pool import HorsePool


@dataclass(frozen=True)
class PoolTrioTicketRule:
    """``axis`` の馬を1頭目、``second`` の馬を2頭目、``third`` の馬を3頭目にする3連複（研究「危険な人気馬を見極める」）。

    1頭目が2頭以上なら1頭目ごとに組み、3頭が違う組だけを、同じ組は1点にまとめる（3つとも同じ集まりなら、その集まりのボックス）。
    ``upset_levels`` があれば、3連複の荒れ具合（``TrioUpsetJudge``）がそのどれかのレースだけで買う（無ければ全レース。選ぶのは ``MarkTickets``）。
    ``min_odds`` があれば、オッズがその倍率に届かない組を外す（外すのは ``TorigamiFilter``）。
    ``totals`` は、この買い方を入れる合計の組（空なら比べるための行）。
    """

    axis: HorsePool
    second: HorsePool
    third: HorsePool
    stake_units: float
    upset_levels: tuple[str, ...] = ()
    min_odds: float | None = None
    totals: tuple[str, ...] = ()
    ticket_type: TicketType = TicketType.TRIO

    @property
    def label(self) -> str:
        """表に出す買い方の名前。例: ``3連複（6番人気以下（複勝オッズとの差 +0.05 以上）−強い人気馬（複勝オッズとの差 -0.05 以上）−
        強い人気馬（複勝オッズとの差 -0.05 以上）・荒れ具合 大荒れ・100倍以上）``。"""
        levels = f"・荒れ具合 {'・'.join(self.upset_levels)}" if self.upset_levels else ""
        odds = f"・{self.min_odds:g}倍以上" if self.min_odds is not None else ""
        return f"{self.ticket_type.label}（{self.axis.label}−{self.second.label}−{self.third.label}{levels}{odds}）"

    def combos(self, axes: list[int], seconds: list[int], thirds: list[int]) -> list[tuple[int, ...]]:
        """``axes``・``seconds``・``thirds`` は1頭目・2頭目・3頭目の馬番。"""
        return sorted({tuple(sorted((axis, second, third)))
                       for axis in axes for second in seconds for third in thirds if len({axis, second, third}) == 3})
