"""1レースの直前の買い目（買う馬の並び。無ければ理由）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .late_pick import LatePick

STAKE = 100


@dataclass(frozen=True)
class LateBets:
    """``announced`` は材料にしたオッズの断面の発表月日時分（MMDDhhmm。無ければ空）。``reason`` は買う馬がいない・出せなかった理由。
    ``closeness`` は線への近さ（``LateRule.closeness``。2つのモデルの値を出せなかったレースは None）。地方の期待度の点数になる。"""

    picks: tuple[LatePick, ...] = ()
    reason: str = ""
    announced: str = ""
    closeness: float | None = None

    @classmethod
    def none(cls, reason: str) -> LateBets:
        return cls((), reason)

    @property
    def empty(self) -> bool:
        return not self.picks

    def lines(self, label: Callable[[int], str] = str) -> list[str]:
        """通知に書く行。買う馬ごとに 単勝・馬単（その馬 → 相手）・3連単（その馬 → 相手 → 相手）。``label`` は馬番の書き方（通知は印を添える）。"""
        return [line for pick in self.picks for line in self._pick_lines(pick, label)]

    def to_dict(self) -> dict[str, Any]:
        return {"買う馬": [pick.to_dict() for pick in self.picks], "理由": self.reason, "オッズの発表月日時分": self.announced,
                "線への近さ": None if self.closeness is None else round(self.closeness, 4)}

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> LateBets:
        picks = tuple(LatePick.from_dict(pick) for pick in body.get("買う馬", []))
        closeness = body.get("線への近さ")
        return cls(picks, str(body.get("理由", "")), str(body.get("オッズの発表月日時分", "")), None if closeness is None else float(closeness))

    @staticmethod
    def _pick_lines(pick: LatePick, label: Callable[[int], str]) -> list[str]:
        axis = label(pick.horse_no)
        lines = [f"単勝 {axis}（決めたときの単勝 {pick.odds:.1f}倍）{STAKE}円"]
        exactas = pick.exactas()
        if exactas:
            seconds = ",".join(label(no) for no in pick.exacta_opponents)
            lines.append(f"馬単 {axis} → {seconds}（{len(exactas)}点 {STAKE * len(exactas):,}円）")
        combos = pick.trifectas()
        if combos:
            others = ",".join(label(no) for no in pick.opponents)
            lines.append(f"3連単 {axis} → {others} → {others}（{len(combos)}点 {STAKE * len(combos):,}円）")
        return lines
