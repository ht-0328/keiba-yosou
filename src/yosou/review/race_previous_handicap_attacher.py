"""これから走る1レースの予測用データに、前走の不利を足す（予測の流れに渡す関数の形）。"""

from __future__ import annotations

from datetime import date

import duckdb

from yosou.shared.dataset import HORSE_ID, OddsInput, PredictionData
from yosou.shared.feature import PredictionTiming

from .previous_handicap_attachment import PreviousHandicapAttachment
from .repository import ReviewStore
from .stored_handicap_lookup import StoredHandicapLookup


class RacePreviousHandicapAttacher:
    """全頭の予想の予測の流れ（``PredictionWorkflow``）の ``extras``・``win_extras`` に渡す関数の形（``attach``）。

    予測用データの馬ID から、保存した馬の回顧ノート（``ReviewStore`` の表3）を ``StoredHandicapLookup`` で引く。
    呼ぶ側が開いている元DB の接続を受け取る。同じレースで続けて呼ばれたら、前の表を使い回す。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, store: ReviewStore) -> None:
        self._lookup = StoredHandicapLookup(con, store)
        self._attachment = PreviousHandicapAttachment()
        self._last: tuple[str, object] | None = None

    def attach(self, data: PredictionData, race_id: str, timing: PredictionTiming, given: OddsInput | None) -> PredictionData:
        if self._last is None or self._last[0] != race_id:
            race_date = date(int(race_id[:4]), int(race_id[4:6]), int(race_id[6:8]))
            horse_ids = [str(horse_id) for horse_id in data.ids[HORSE_ID]]
            self._last = (race_id, self._lookup.of(race_id, race_date, horse_ids))
        return self._attachment.apply(data, self._last[1])
