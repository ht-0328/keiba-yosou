"""過去の WIN5 で、対象レースごとに当日と前日のどちらの予測を使うかを、発走時刻でまねる。"""

from __future__ import annotations

from collections.abc import Sequence

from yosou.shared.feature import PredictionTiming

#: 1レース目の発走からこの分数以上あとに発走するレースは、締め切りの時点で馬体重が出ていないとみなす（設計書 07・15 の 10。仮の値）。
WEIGHT_UNKNOWN_MINUTES = 60


class Win5LegTiming:
    """設計書「近走と適性からWIN5の買い目を決める」07 の「過去のレースで確かめるときの時点のまね方」。1レース目の発走時刻から 60分以上あとに
    発走するレースは前日の予測、それより前に発走するレース（1レース目を含む）は当日の予測にする。発走時刻が読めないレースは前日にする
    （馬体重が出ていたと言えないため）。"""

    def __init__(self, minutes: int = WEIGHT_UNKNOWN_MINUTES) -> None:
        self._minutes = minutes

    def of(self, post_times: Sequence[str | None]) -> tuple[PredictionTiming, ...]:
        """発売の順の発走時刻（``HHMM``）から、レースごとの時点。"""
        first = self._minutes_of(post_times[0])
        return tuple(self._timing(first, self._minutes_of(each)) for each in post_times)

    def _timing(self, first: int | None, minutes: int | None) -> PredictionTiming:
        if first is None or minutes is None or minutes - first >= self._minutes:
            return PredictionTiming.DAY_BEFORE
        return PredictionTiming.RACE_DAY

    def _minutes_of(self, text: str | None) -> int | None:
        value = (text or "").strip()
        if len(value) != 4 or not value.isdigit():
            return None
        return int(value[:2]) * 60 + int(value[2:])
