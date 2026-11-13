"""WIN5 の日を表す値。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

#: 土曜の ``date.weekday()``。
_SATURDAY = 5


@dataclass(frozen=True)
class Win5Day:
    """WIN5 の1日。開催日・対象レース5つのレースID（発売の順）・キャリーオーバー金額初期（円）。

    ``Win5DayRepository`` が返す値なので ``repository/`` に置く（手本の ``TargetScope`` と同じ）。
    """

    race_date: date
    race_ids: tuple[str, ...]
    carry: int

    @property
    def is_saturday(self) -> bool:
        """土曜の WIN5 か（日曜・祝日の月曜などは偽）。発売票数の見積もりを分けるのに使う。"""
        return self.race_date.weekday() == _SATURDAY
