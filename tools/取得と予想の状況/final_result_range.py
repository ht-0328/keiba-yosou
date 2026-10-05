"""中央の確定成績が DB にどこからどこまで入っているか。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FinalResultRange:
    """確定成績（データ区分 5〜7）のある中央のレースの、最初と最後の開催日（``YYYY-MM-DD``）とレース数。無ければ日付は None。"""

    first_date: str | None
    last_date: str | None
    races: int
