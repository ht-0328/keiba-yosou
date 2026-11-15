"""券種ごとの買い目の形1つ（軸と並び・相手の範囲・オッズと期待値の線）。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations

from .race_horses import RaceHorses

#: 券種の名前。
WIN, PLACE, BRACKET, QUINELLA, WIDE, EXACTA, TRIO, TRIFECTA = "単勝", "複勝", "枠連", "馬連", "ワイド", "馬単", "3連複", "3連単"
TICKETS: tuple[str, ...] = (WIN, PLACE, BRACKET, QUINELLA, WIDE, EXACTA, TRIO, TRIFECTA)
#: 1券種の点数の上限（設計書 16 の 6.1）。超えた分は組の期待値の高い順に残す。
MAX_POINTS = 24


@dataclass(frozen=True)
class TicketShape:
    """買い目の形1つ。

    - ``ticket``: 券種。``form``: 軸と並び（例 ``◎→相手``）。``partners``: 相手の範囲（例 ``○▲☆``。形で決まるものは空）。
    - ``cap``: オッズの上限（None なら無し）。``floor``: 最低オッズの下限（ワイド）。``line``: 組の期待値の線（複勝は複勝の期待値の線）。
    - ``star``: 複勝で、買い目に入れる ☆ を足すか。
    """

    ticket: str
    form: str
    partners: str = ""
    cap: float | None = None
    floor: float | None = None
    line: float | None = None
    star: bool = False

    @property
    def name(self) -> str:
        parts = [self.form + (f"（相手 {self.partners}）" if self.partners else "")]
        if self.star:
            parts.append("☆を足す")
        if self.cap is not None:
            parts.append(f"{self.cap:g}倍まで")
        if self.floor is not None:
            parts.append(f"{self.floor:g}倍から")
        if self.line is not None:
            parts.append(f"期待値 {self.line:g} 以上")
        return "・".join(parts)

    def combos(self, horses: RaceHorses) -> list[tuple[int, ...]]:
        """この形で組む組（馬番の組。着順を区別する券種は1着から順。順不同の券種は小さい順）。枠連は枠番の組。"""
        top = horses.top
        if top is None:
            return []
        builder = getattr(self, f"_{_KEYS[self.ticket]}")
        return _unique(builder(horses, top))

    def _win(self, horses: RaceHorses, top: int) -> list[tuple[int, ...]]:
        return [(top,)]

    def _place(self, horses: RaceHorses, top: int) -> list[tuple[int, ...]]:
        count = {"◎": 1, "◎・○": 2, "◎・○・▲": 3}[self.form]
        chosen = [horse for horse in (top, horses.second, horses.third)[:count] if horse is not None]
        if self.star and horses.star is not None:
            chosen.append(horses.star)
        return [(horse,) for horse in chosen]

    def _bracket(self, horses: RaceHorses, top: int) -> list[tuple[int, ...]]:
        if top not in horses.frames:
            return []
        own = horses.frames[top]
        others = {horses.frames[horse] for horse in horses.partners(self.partners, (top,)) if horse in horses.frames}
        return [tuple(sorted((own, frame))) for frame in sorted(others)]

    def _quinella(self, horses: RaceHorses, top: int) -> list[tuple[int, ...]]:
        if self.form == "◎○▲の3頭の組":
            box = [horse for horse in (top, horses.second, horses.third) if horse is not None]
            return [tuple(sorted(pair)) for pair in combinations(box, 2)]
        return [tuple(sorted((top, horse))) for horse in horses.partners(self.partners, (top,))]

    def _wide(self, horses: RaceHorses, top: int) -> list[tuple[int, ...]]:
        if self.form == "◎○−相手":
            axes = [horse for horse in (top, horses.second) if horse is not None]
            pool = horses.partners(self.partners, ())
            return [tuple(sorted((axis, horse))) for axis in axes for horse in pool if horse != axis]
        return [tuple(sorted((top, horse))) for horse in horses.partners(self.partners, (top,))]

    def _exacta(self, horses: RaceHorses, top: int) -> list[tuple[int, ...]]:
        pool = horses.partners(self.partners, (top,))
        forward = [(top, horse) for horse in pool]
        backward = [(horse, top) for horse in pool]
        return {"◎→相手": forward, "相手→◎": backward, "◎と相手の両方向": forward + backward}[self.form]

    def _trio(self, horses: RaceHorses, top: int) -> list[tuple[int, ...]]:
        if self.form == "◎○▲△の4頭の組":
            box = [horse for horse in (top, horses.second, horses.third, *horses.triangles[:1]) if horse is not None]
            return [tuple(sorted(three)) for three in combinations(box, 3)]
        if self.form == "◎軸−印−無印に流す":
            marks = horses.partners("印", (top,))
            rest = horses.partners("無印に流す", (top,))
            return [tuple(sorted((top, mark, other))) for mark in marks for other in rest if other != mark]
        if self.form == "◎○の2頭軸−相手":
            if horses.second is None:
                return []
            return [tuple(sorted((top, horses.second, horse))) for horse in horses.partners(self.partners, (top, horses.second))]
        pool = horses.partners(self.partners, (top,))
        return [tuple(sorted((top, *pair))) for pair in combinations(pool, 2)]

    def _trifecta(self, horses: RaceHorses, top: int) -> list[tuple[int, ...]]:
        if self.form == "○▲→消以外→◎":
            heads = [horse for horse in (horses.second, horses.third) if horse is not None]
            middles = horses.partners("無印に流す", (top,))
            return [(head, middle, top) for head in heads for middle in middles if middle != head]
        if self.form == "◎→○▲→無印に流す":
            seconds = [horse for horse in (horses.second, horses.third) if horse is not None]
            thirds = horses.partners("無印に流す", (top,))
            return [(top, second, third) for second in seconds for third in thirds if third != second]
        pool = horses.partners(self.partners, (top,))
        pairs = list(permutations(pool, 2))
        place = {"◎→相手→相手": 0, "相手→◎→相手": 1, "相手→相手→◎": 2}[self.form]
        return [tuple(pair[:place]) + (top,) + tuple(pair[place:]) for pair in pairs]


_KEYS = {WIN: "win", PLACE: "place", BRACKET: "bracket", QUINELLA: "quinella", WIDE: "wide", EXACTA: "exacta",
         TRIO: "trio", TRIFECTA: "trifecta"}


def combo_key(ticket: str, combo: tuple[int, ...]) -> str:
    """払戻・オッズの表の組番。枠連は1文字が1つの枠（例 (3, 6) → ``36``）、ほかは馬番を2桁ずつ並べる（例 (1, 5) → ``0105``）。"""
    if ticket == BRACKET:
        return "".join(str(int(frame)) for frame in combo)
    return "".join(f"{int(horse):02d}" for horse in combo)


def _unique(combos: list[tuple[int, ...]]) -> list[tuple[int, ...]]:
    seen: dict[tuple[int, ...], None] = {}
    for combo in combos:
        seen.setdefault(tuple(int(value) for value in combo), None)
    return list(seen)
