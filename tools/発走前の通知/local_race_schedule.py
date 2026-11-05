"""その日の地方のレースの一覧（発走時刻つき）を、地方の元DB から発走の早い順に読む。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from 共通 import db
from 共通.local_codes import LOCAL_VENUE_NAMES

from 発走前の通知.local_race_repository import LocalRaceRepository
from 発走前の通知.local_race_row import LocalRaceRow
from 発走前の通知.scheduled_race import ScheduledRace

#: 発走時刻の桁数（HHMM）。
_POST_LENGTH = 4


class LocalRaceSchedule:
    """中央の ``RaceSchedule`` の地方版。DB は読むたびに開いてすぐ閉じる（nvdata-store の取り込みの邪魔をしない）。
    地方の出馬表は数日先まで nvstore sync で入り、発走時刻の変更は速報（0B14）で入るので、呼ぶ側は待つ間にも読み直す。"""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path

    def read(self, day: str) -> list[ScheduledRace]:
        with db.open_db(self._db_path, default=db.LOCAL) as con:
            rows = LocalRaceRepository(con).read(day)
        return self.from_rows(day, rows)

    @staticmethod
    def from_rows(day: str, rows: Sequence[LocalRaceRow]) -> list[ScheduledRace]:
        """発走時刻のあるレースを発走の早い順に。競馬場コードは名前（門別・船橋 …）にする。"""
        races = [LocalRaceSchedule._race(day, row) for row in rows if len(row.post) == _POST_LENGTH]
        return sorted(races, key=lambda race: (race.post, race.rid))

    @staticmethod
    def _race(day: str, row: LocalRaceRow) -> ScheduledRace:
        post = datetime.fromisoformat(f"{day}T{row.post[:2]}:{row.post[2:]}:00")
        venue = LOCAL_VENUE_NAMES.get(row.venue_code, row.venue_code)
        return ScheduledRace(rid=row.rid, venue=venue, number=row.number, name=row.name, post=post)
