"""直前の買い目の1頭ぶん: 単勝を買う馬と、その馬を1着に固定した 馬単・3連単の相手。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Any


@dataclass(frozen=True)
class LatePick:
    """``odds`` は決めたときの単勝オッズ（確定ではない）。``opponents`` は 3連単の相手（軸を除いた人気順。決めたときの単勝オッズの低い順）。
    ``exacta_opponents`` は馬単の相手（軸を除いた、全頭の予想の 3着以内の確率の高い順）。"""

    horse_no: int
    odds: float
    likeness: float
    payback: float
    opponents: tuple[int, ...]
    exacta_opponents: tuple[int, ...] = ()

    def exactas(self) -> list[tuple[int, int]]:
        """馬単の組（軸 → 相手）。"""
        return [(self.horse_no, second) for second in self.exacta_opponents]

    def trifectas(self) -> list[tuple[int, int, int]]:
        """3連単の組（軸 → 相手 → 相手）。相手が2頭に満たなければ空。"""
        return [(self.horse_no, second, third) for second, third in permutations(self.opponents, 2)]

    def to_dict(self) -> dict[str, Any]:
        return {"馬番": self.horse_no, "単勝オッズ": self.odds, "買う馬らしさ": round(self.likeness, 4), "戻りの見込み": round(self.payback, 4),
                "相手": list(self.opponents), "馬単の相手": list(self.exacta_opponents)}

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> LatePick:
        return cls(int(body["馬番"]), float(body["単勝オッズ"]), float(body["買う馬らしさ"]), float(body["戻りの見込み"]),
                   tuple(int(no) for no in body["相手"]), tuple(int(no) for no in body.get("馬単の相手", [])))
