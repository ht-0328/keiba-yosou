"""高知ファイナルの1レースの印と買い目（出せなければ理由）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STAKE = 100
#: 券種の並び（通知に書く順）。
WIN_BET = "単勝"
QUINELLA = "馬連"
EXACTA = "馬単"
TRIFECTA = "3連単"
PLACE = "複勝"
WIDE = "ワイド"
TRIO = "3連複"
BET_ORDER: tuple[str, ...] = (WIN_BET, QUINELLA, EXACTA, TRIFECTA, PLACE, WIDE, TRIO)
#: ◎ の複勝の見込みで買うか決める券種。
PLACE_BETS: tuple[str, ...] = (PLACE, WIDE, TRIO)
#: 着順を問わない券種（馬番の小さい順に書く）。
_UNORDERED: tuple[str, ...] = (QUINELLA, WIDE, TRIO)


@dataclass(frozen=True)
class FinalBets:
    """``head`` は ◎、``partners`` は相手（予想の高い順。先頭2頭が ○▲、残りが △）、``favorite`` はそのときの1番人気（◎ にしない）。
    ``tickets`` は 券種 → 買う組（馬番の並び）。``place_value`` は ◎ の複勝の見込み（3着以内の確率 × 複勝オッズの低いほう）、
    ``place_line`` は 複勝・ワイド・3連複を買う線。``announced`` は材料にしたオッズの断面の発表月日時分。``reason`` は出せなかった理由。"""

    head: int | None = None
    partners: tuple[int, ...] = ()
    favorite: int | None = None
    tickets: dict[str, tuple[tuple[int, ...], ...]] = field(default_factory=dict)
    place_value: float | None = None
    place_line: float = 0.0
    announced: str = ""
    reason: str = ""

    @classmethod
    def none(cls, reason: str) -> FinalBets:
        return cls(reason=reason)

    @property
    def empty(self) -> bool:
        return self.head is None

    @property
    def points(self) -> int:
        return sum(len(combos) for combos in self.tickets.values())

    @property
    def yen(self) -> int:
        return STAKE * self.points

    def lines(self) -> list[str]:
        """通知に書く行: 印、券種ごとの組、複勝・ワイド・3連複を見送るときはその理由。"""
        if self.empty:
            return []
        marks = [f"◎{self.head}", *(f"{mark}{no}" for mark, no in zip("○▲", self.partners))]
        if len(self.partners) > 2:
            marks.append("△" + ",".join(str(no) for no in self.partners[2:]))
        lines = [" ".join(marks) + f"（1番人気 {self.favorite} は ◎ にしない）"]
        lines += [self._bet_line(name) for name in BET_ORDER if self.tickets.get(name)]
        if not any(self.tickets.get(name) for name in PLACE_BETS) and self.place_value is not None:
            lines.append(f"複勝・ワイド・3連複: 見送り（◎ の複勝の見込み {self.place_value:.2f}。{self.place_line:.2f} 以上で買う）")
        return lines

    def to_dict(self) -> dict[str, Any]:
        return {"◎": self.head, "相手": list(self.partners), "1番人気": self.favorite,
                "買い目": {name: [list(combo) for combo in combos] for name, combos in self.tickets.items()},
                "◎の複勝の見込み": None if self.place_value is None else round(self.place_value, 4), "複勝などを買う線": self.place_line,
                "オッズの発表月日時分": self.announced, "理由": self.reason}

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> FinalBets:
        tickets = {name: tuple(tuple(int(no) for no in combo) for combo in combos) for name, combos in body.get("買い目", {}).items()}
        value = body.get("◎の複勝の見込み")
        return cls(body.get("◎"), tuple(int(no) for no in body.get("相手", [])), body.get("1番人気"), tickets,
                   None if value is None else float(value), float(body.get("複勝などを買う線", 0.0)),
                   str(body.get("オッズの発表月日時分", "")), str(body.get("理由", "")))

    def _bet_line(self, name: str) -> str:
        combos = self.tickets[name]
        joiner = "−" if name in _UNORDERED else "→"
        text = " / ".join(joiner.join(str(no) for no in combo) for combo in combos)
        return f"{name} {text}（{len(combos)}点 {STAKE * len(combos):,}円）"
