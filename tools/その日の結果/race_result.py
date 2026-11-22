"""1レースの予想と結果を突き合わせた1行。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from 今週の予想.logic_forecast import LogicForecast
from 今週の予想.mark_return import MarkReturn

from その日の結果.day_payouts import DayPayouts

#: 買う計画の複勝の券種。
_PLACE = "複勝"


@dataclass(frozen=True)
class Settled:
    """買った金額と戻った金額。``unknown`` は払戻を読めなかった券種（知らない名前の券種）の金額。"""

    stake: int = 0
    back: int = 0
    unknown: int = 0

    def text(self) -> str:
        if not self.stake:
            return "買わない"
        note = f"（うち {self.unknown:,}円は払戻を読めない券種）" if self.unknown else ""
        return f"{self.stake:,}円 → {self.back:,}円{note}"


class RaceResult:
    """予想の JSON（印・買う計画・印の買い目）と、その日の着順・払戻から、1レースの結果を作る。

    - ``top3``: 1〜3着の馬番と、その馬の印（例 ``1着 11◎・2着 3△・3着 12▲``）。
    - ``plan``: 実際に買う買い目（買う計画の複勝・単勝・馬単・組の券種）の精算。
    - ``marks``: 全レースの印の買い目（AI だけの予想。「買う」のレースだけ数える）の精算。
    - ``logic``: AI＋ロジック予想（展開・クラスのロジックで見送ったレースは買わない）の精算。
    """

    def __init__(self, forecast: dict[str, Any], finishes: list[tuple[int, int]], payouts: DayPayouts,
                 styles: Mapping[int, str]) -> None:
        self._forecast = forecast
        self._finishes = finishes
        self._payouts = payouts
        self._styles = styles
        self._rid = str(forecast["rid"])

    @property
    def finished(self) -> bool:
        """着順と払戻が届いているか。"""
        return bool(self._finishes) and self._payouts.has(self._rid)

    def marks_line(self) -> str:
        """印の1行（例 ``◎11 ○13 ▲12``。◎○▲ だけ）。"""
        return " ".join(f"{mark}{self._horse(mark)}" for mark in ("◎", "○", "▲") if self._horse(mark) is not None)

    def top3(self) -> str:
        marks = {int(horse["horse_no"]): horse["mark"] for horse in self._forecast["horses"] if horse.get("horse_no") is not None}
        return "・".join(f"{finish}着 {number}{marks.get(number, '')}" for finish, number in self._finishes)

    def top_finish(self) -> str:
        """◎ の着順（1〜3着なら ``1着``、それ以外は ``着外``）。"""
        top = self._horse("◎")
        return next((f"{finish}着" for finish, number in self._finishes if number == top), "着外")

    def plan(self) -> Settled:
        plan = self._forecast.get("plan") or {}
        tickets = [(_PLACE, f"{int(pick['horse_no']):02d}", int(pick["yen"])) for pick in plan.get("picks") or ()]
        tickets += [(ticket["ticket_type"], ticket["combo"], int(ticket["yen"])) for ticket in plan.get("tickets") or ()]
        return self._settle(tickets)

    def marks(self) -> Settled:
        found = MarkReturn.of(self._forecast)
        if found is None or not found.buys:
            return Settled()
        return self._settle([(ticket["ticket_type"], ticket["combo"], yen) for rows in found.stakes.values() for ticket, _, yen in rows])

    def logic(self) -> Settled:
        return Settled() if self.logic_skip() else self.marks()

    def logic_skip(self) -> str:
        """AI は買い、AI＋ロジック予想は見送ったレースなら、当たったロジックの名前（展開・クラス）。そうでなければ空。"""
        skip = LogicForecast().skip(self._forecast, self._styles)
        return skip.name if skip is not None else ""

    def _settle(self, tickets: list[tuple[str, str, int]]) -> Settled:
        stake = back = unknown = 0
        for ticket_type, combo, yen in tickets:
            stake += yen
            paid = self._payouts.yen(self._rid, ticket_type, combo)
            if paid is None:
                unknown += yen
            else:
                back += paid * yen // 100
        return Settled(stake, back, unknown)

    def _horse(self, mark: str) -> int | None:
        return next((int(horse["horse_no"]) for horse in self._forecast["horses"]
                     if horse.get("mark") == mark and horse.get("horse_no") is not None), None)
