"""参加パターンの一覧。"""

from __future__ import annotations

from ..ticket import Breadth
from .all_races_pattern import AllRacesPattern
from .confident_races_pattern import ConfidentRacesPattern
from .race_pattern import RacePattern
from .union_pattern import UnionPattern
from .upset_races_pattern import UpsetRacesPattern
from .weekly_mode import WeeklyMode
from .weekly_top_pattern import WeeklyTopPattern
from .weekly_with_graded_pattern import WeeklyWithGradedPattern

#: 探索で回す参加パターン（①〜⑥。①は切り替え・広め固定・少点数固定の3つ、⑤⑥は荒れる・自信・両方の3つ）。
PATTERNS: tuple[RacePattern, ...] = (
    AllRacesPattern(None), AllRacesPattern(Breadth.WIDE), AllRacesPattern(Breadth.NARROW),
    UpsetRacesPattern(), ConfidentRacesPattern(), UnionPattern(),
    *(WeeklyTopPattern(mode) for mode in WeeklyMode),
    *(WeeklyWithGradedPattern(WeeklyTopPattern(mode)) for mode in WeeklyMode),
)
PATTERNS_BY_KEY: dict[str, RacePattern] = {pattern.key: pattern for pattern in PATTERNS}
if len(PATTERNS_BY_KEY) != len(PATTERNS):
    raise ImportError("参加パターンの鍵が重なっています")


def pattern_by_key(key: str) -> RacePattern:
    """鍵から参加パターンを返す。知らなければ ``LookupError``。"""
    if key not in PATTERNS_BY_KEY:
        raise LookupError(f"知らない参加パターンです: {key}（{' / '.join(PATTERNS_BY_KEY)}）")
    return PATTERNS_BY_KEY[key]
