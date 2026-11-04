"""その日の平地のレースの一覧（発走時刻つき）を、元DB から発走の早い順に読む。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from 共通 import card, db

from 発走前の通知.scheduled_race import ScheduledRace

#: レース一覧の列名 → 位置。
_COLUMN = {name: index for index, name in enumerate(card.CARD_LIST_HEADERS)}
#: 障害レースのコースの書き出し（予想の対象外）。
_JUMP_PREFIX = "障害"


class RaceSchedule:
    """その日のレースを、道具「今週の出馬表」のレース一覧から読む。DB は読むたびに開いてすぐ閉じる（取り込みの邪魔をしない）。
    発走時刻の変更（速報 0B14）を拾えるように、呼ぶ側は待つ間にも読み直す。"""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path

    def read(self, day: str) -> list[ScheduledRace]:
        with db.open_db(self._db_path) as con:
            listed = card.list_cards(con, date_from=day, date_to=day, limit=card.MAX_LIST_LIMIT)
        return self.from_rows(day, listed.rows)

    @staticmethod
    def from_rows(day: str, rows: Sequence[Sequence[Any]]) -> list[ScheduledRace]:
        """レース一覧の行から、発走時刻のある平地のレースを発走の早い順に。"""
        races = [RaceSchedule._race(day, row) for row in rows if RaceSchedule._is_flat_with_time(row)]
        return sorted(races, key=lambda race: (race.post, race.rid))

    @staticmethod
    def _is_flat_with_time(row: Sequence[Any]) -> bool:
        return bool(row[_COLUMN["発走"]]) and not str(row[_COLUMN["コース"]] or "").startswith(_JUMP_PREFIX)

    @staticmethod
    def _race(day: str, row: Sequence[Any]) -> ScheduledRace:
        post = datetime.fromisoformat(f"{day}T{row[_COLUMN['発走']]}:00")
        return ScheduledRace(rid=str(row[_COLUMN["rid"]]), venue=str(row[_COLUMN["場"]]), number=int(row[_COLUMN["R"]]),
                             name=str(row[_COLUMN["レース名"]] or ""), post=post)
