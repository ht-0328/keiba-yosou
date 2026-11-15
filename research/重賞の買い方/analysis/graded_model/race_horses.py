"""1つの重賞の、印ごとの馬と、買い目の相手に使う馬の集まり。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 今週の予想.forecast_columns import MARK, PLACE_VALUE, PROBABILITY
from 今週の予想.mark_rule import NOTE_MARK, OUT_MARK, TOP_MARK, VALUE_MARK
from 今週の予想.ticket_rules import PLACE_VALUE_LINE

from .graded_race_marker import FRAME_NO

#: 印の並び（○▲ と △ の3頭）。
SECOND, THIRD, TRIANGLE = "○", "▲", "△"


@dataclass(frozen=True)
class RaceHorses:
    """1つの重賞の馬の集まり（馬番）。

    - ``top``・``second``・``third``: ◎・○・▲（いなければ None）。``triangles``: △ の馬（3着以内の確率の順）。
    - ``star``: 買い目の相手に入れる ☆（複勝の期待値が線 1.25 以上のときだけ。表示だけの ☆ は入れない）。``note``: 注。
    - ``unmarked_top``: 印の無い馬（消を除く）のうち、3着以内の確率の上位3頭。``alive``: 消を除いた全頭（3着以内の確率の順）。
    - ``frames``: 馬番 → 枠番。
    """

    top: int | None
    second: int | None
    third: int | None
    triangles: tuple[int, ...]
    star: int | None
    note: int | None
    unmarked_top: tuple[int, ...]
    alive: tuple[int, ...]
    frames: dict[int, int]

    @classmethod
    def of(cls, race: pd.DataFrame) -> RaceHorses:
        """``race`` は印を付けた1レースの表（``GradedRaceMarker.mark`` の1レース分）。"""
        table = race.sort_values(PROBABILITY, ascending=False)

        def first(mark: str) -> int | None:
            found = table.loc[table[MARK] == mark, "horse_no"]
            return int(found.iloc[0]) if len(found) else None

        stars = table[(table[MARK] == VALUE_MARK) & (table[PLACE_VALUE] >= PLACE_VALUE_LINE)]
        unmarked = table[table[MARK] == "－"]
        alive = table[table[MARK] != OUT_MARK]
        frames = {int(horse): int(frame) for horse, frame in zip(table["horse_no"], table[FRAME_NO]) if pd.notna(frame)}
        return cls(first(TOP_MARK), first(SECOND), first(THIRD),
                   tuple(int(horse) for horse in table.loc[table[MARK] == TRIANGLE, "horse_no"]),
                   int(stars["horse_no"].iloc[0]) if len(stars) else None, first(NOTE_MARK),
                   tuple(int(horse) for horse in unmarked["horse_no"].head(3)),
                   tuple(int(horse) for horse in alive["horse_no"]), frames)

    def marked(self) -> tuple[int, ...]:
        """印の馬（◎○▲△☆注。☆ は買い目に入れるものだけ）。"""
        return _present((self.top, self.second, self.third, *self.triangles, self.star, self.note))

    def partners(self, name: str, axis: tuple[int, ...]) -> tuple[int, ...]:
        """相手の範囲 ``name`` の馬（軸 ``axis`` を除く）。"""
        pools = {
            "○▲": (self.second, self.third),
            "○▲☆": (self.second, self.third, self.star),
            "○▲△": (self.second, self.third, *self.triangles),
            "○▲△☆": (self.second, self.third, *self.triangles, self.star),
            "☆注": (self.star, self.note),
            "印": self.marked(),
            "印と上位の無印3頭": (*self.marked(), *self.unmarked_top),
            "無印に流す": self.alive,
        }
        return tuple(horse for horse in _present(pools[name]) if horse not in axis)


def _present(horses) -> tuple[int, ...]:
    """None を除き、重なりを除いた並び。"""
    seen: list[int] = []
    for horse in horses:
        if horse is not None and horse not in seen:
            seen.append(horse)
    return tuple(seen)
