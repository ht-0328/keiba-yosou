"""終わったレースの回顧（表2・表3）を作って保存し、買い目の記録（表1）に払戻を書き足す。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from . import names
from .bet_settler import BetSettler
from .handicap_history import HandicapHistory
from .race_reviews import RaceReviews
from .repository import ReviewRunRepository, ReviewStore


class ReviewWorkflow:
    """元DB の終わった出走（``ReviewRunRepository``）から、``after`` 以降（省略すると、前に書いた範囲の次の日以降）のレースの
    表2（``RaceReviews``）と表3（``HandicapHistory``。不利のあった馬だけ）を作って ``ReviewStore`` に書き、表1の未精算の買い目に
    払戻を書き足す（``BetSettler``）。人が手で書く列は無い。

    ``forecast_paces`` は予想したときに残したペースの確率（``race_id``・予想のハイの確率・予想のスローの確率）。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store
        self._history = HandicapHistory()
        self._reviews = RaceReviews()
        self._settler = BetSettler(store)

    def run(self, con: duckdb.DuckDBPyConnection, after: date | None = None,
            forecast_paces: pd.DataFrame | None = None) -> dict[str, int]:
        """書いた行の数（表ごと）と、精算した買い目の数。"""
        runs = ReviewRunRepository(con).read()
        if runs.empty:
            return {names.RACES_TABLE: 0, names.HORSES_TABLE: 0, names.BETS_TABLE: 0}
        start = after or self._next_day()
        handicaps = self._history.of(runs, after=start)
        flagged = handicaps[handicaps[names.DEGREE] >= 1]
        races = self._reviews.of(runs, forecast_paces, after=None if start is None else pd.Timestamp(start))
        written = {names.RACES_TABLE: self._store.write(names.RACES_TABLE, races),
                   names.HORSES_TABLE: self._store.write(names.HORSES_TABLE, flagged)}
        last = runs["race_date"].max().date()
        self._store.set_as_of(last)
        written[names.BETS_TABLE] = self._settler.settle(runs, con)
        return written

    def _next_day(self) -> date | None:
        as_of = self._store.as_of()
        return None if as_of is None else as_of   # 同じ日はもう一度書く（その日の途中で回したとき、後のレースを書き足す）
