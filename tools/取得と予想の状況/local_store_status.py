"""地方（nvdata-store）の取得の状況。"""

from __future__ import annotations

from dataclasses import dataclass, field

from 取得と予想の状況.acquisition_day import AcquisitionDay
from 取得と予想の状況.final_result_range import FinalResultRange
from 取得と予想の状況.store_file import StoreFile
from 取得と予想の状況.store_screen import StoreScreen
from 取得と予想の状況.sync_record import SyncRecord


@dataclass(frozen=True)
class LocalStoreStatus:
    """``LocalStoreReader.read`` の結果。``db_error`` があれば DB は読めておらず（nvdata-store の取得中など）、DB から読む項目は空。
    DB のファイルが無いときも DB から読む項目は空（``file.exists`` が偽）。``days`` は今日以降の開催日ごとの数え上げ。
    """

    store: StoreScreen
    file: StoreFile
    db_error: str | None
    results: FinalResultRange | None
    sync_records: list[SyncRecord] = field(default_factory=list)
    days: list[AcquisitionDay] = field(default_factory=list)
