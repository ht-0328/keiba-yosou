"""1開催日ぶんの、レース前の材料が DB に何レースぶん入っているか（中央と地方で同じ数え方）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from 共通 import card
from 共通.race_signals import RaceSignals


@dataclass(frozen=True)
class AcquisitionDay:
    """1開催日の、レース数と「何が何レースぶん入っているか」。数はすべてレース数。

    ``latest_odds_at`` は、その日のレースに入った締め切り前のオッズのうち、いちばん新しい発表時刻（無ければ None）。
    """

    day: str
    weekday: str
    venues: tuple[str, ...]
    races: int
    name_lists: int
    cards: int
    finished: int
    cancelled: int
    with_odds: int
    latest_odds_at: datetime | None
    weighed: int
    going_announced: int

    @classmethod
    def summarize(cls, day: str, signals: list[RaceSignals]) -> "AcquisitionDay":
        """その日のレースの並びから数える。"""
        odds_times = [moment for moment in (each.odds_announced_datetime() for each in signals) if moment is not None]
        return cls(
            day=day, weekday=card.weekday_of(day), venues=tuple(dict.fromkeys(each.venue for each in signals)), races=len(signals),
            name_lists=sum(each.is_name_list for each in signals), cards=sum(each.is_card for each in signals),
            finished=sum(each.is_finished for each in signals), cancelled=sum(each.is_cancelled for each in signals),
            with_odds=sum(each.has_odds for each in signals), latest_odds_at=max(odds_times, default=None),
            weighed=sum(each.is_weighed for each in signals), going_announced=sum(each.going_announced for each in signals),
        )
