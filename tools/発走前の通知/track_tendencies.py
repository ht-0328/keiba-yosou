"""1レースの前に、同じ日・同じ競馬場・同じ芝ダの先に終わったレースから馬場の傾向（``TrackTendency``）を出す。中央と地方。"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from 共通 import db

from 発走前の通知.position_counts import PositionCounts
from 発走前の通知.top3_positions import Top3Positions
from 発走前の通知.track_tendency import TrackTendency
from 発走前の通知.venue_run_repository import VenueRunRepository

#: いつもの割合を数える期間（その日の前の日までの年数）。
USUAL_YEARS = 3
#: 傾向を出す芝ダ（障害は出さない）。
_SURFACES = ("芝", "ダート")


class TrackTendencies:
    """``of`` はレースごとに元DB を開いてすぐ閉じる（取り込みの邪魔をしない）。いつもの割合は 競馬場 × 芝ダ × 開催日 ごとに
    1回だけ数えてとっておく（通知は1日1つのプロセスなので、2回目からはその日の分を読むだけ）。"""

    def __init__(self, db_path: str | Path | None = None, default: db.DatabaseDefault = db.JRA,
                 counter: Top3Positions | None = None) -> None:
        self._db_path = db_path
        self._default = default
        self._counter = counter or Top3Positions()
        self._usual: dict[tuple[str, str, str], PositionCounts] = {}

    def of(self, rid: str, venue: str) -> TrackTendency | None:
        """そのレースより前（レース番号が小さい）に終わった、同じ芝ダのレースが無ければ None。"""
        venue_code, day = rid[8:10], date(int(rid[:4]), int(rid[4:6]), int(rid[6:8]))
        with db.open_db(self._db_path, default=self._default) as con:
            repository = VenueRunRepository(con)
            runs = repository.read(venue_code, day, day)
            target = runs[runs["race_id"] == rid]
            if target.empty or target["surface"].iloc[0] not in _SURFACES:
                return None
            surface, race_no = str(target["surface"].iloc[0]), int(target["race_no"].iloc[0])
            today = self._counter.count(runs[(runs["surface"] == surface) & (runs["race_no"] < race_no)])
            if today.top3 == 0:
                return None
            usual = self._usual_counts(repository, venue_code, surface, day)
        return TrackTendency(venue=venue, surface=surface, today=today, usual=usual)

    def _usual_counts(self, repository: VenueRunRepository, venue_code: str, surface: str, day: date) -> PositionCounts:
        key = (venue_code, surface, f"{day:%Y%m%d}")
        if key not in self._usual:
            past = repository.read(venue_code, day - timedelta(days=365 * USUAL_YEARS), day - timedelta(days=1))
            for one in _SURFACES:
                self._usual[(venue_code, one, key[2])] = self._counter.count(self._only(past, one))
        return self._usual[key]

    @staticmethod
    def _only(runs: pd.DataFrame, surface: str) -> pd.DataFrame:
        return runs[runs["surface"] == surface]
