"""取得と予想の状況の全部（1回の確認の結果）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from 取得と予想の状況.day_status import DayStatus
from 取得と予想の状況.final_result_range import FinalResultRange
from 取得と予想の状況.local_store_status import LocalStoreStatus
from 取得と予想の状況.model_folder import ModelFolder
from 取得と予想の状況.race_status import RaceStatus
from 取得と予想の状況.store_file import StoreFile
from 取得と予想の状況.store_screen import StoreScreen
from 取得と予想の状況.sync_record import SyncRecord


@dataclass(frozen=True)
class Overview:
    """``OverviewReader.read`` の結果。``store`` から ``next_race`` までが中央（jvdata-store）、``local`` が地方（nvdata-store）。

    ``db_error`` があれば中央の DB は読めておらず（取得中など）、DB から読む項目は空。``days`` は今日以降の開催日ごとの数え上げ、
    ``day`` はレースごとの表に出す開催日、``races`` はその日のレース、``next_race`` は今日の、これから発走するいちばん早いレース
    （今日のレースを見ていないときは None）。``local`` は地方を見ないとき None。
    """

    now: datetime
    store: StoreScreen
    db_file: StoreFile
    db_error: str | None
    results: FinalResultRange | None
    sync_records: list[SyncRecord] = field(default_factory=list)
    days: list[DayStatus] = field(default_factory=list)
    day: str | None = None
    races: list[RaceStatus] = field(default_factory=list)
    next_race: RaceStatus | None = None
    models: list[ModelFolder] = field(default_factory=list)
    missing_model_roots: list[str] = field(default_factory=list)
    local: LocalStoreStatus | None = None
