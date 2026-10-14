"""保存した馬の回顧ノート（表3）から、これから走る馬の前走の不利を引く。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from . import names
from .features import PREVIOUS_BIAS, PREVIOUS_HANDICAP_NAMES, PREVIOUS_LATE_START, PREVIOUS_MAX, PREVIOUS_PACE, PREVIOUS_REVIEW
from .repository import PreviousRunRepository, ReviewStore


class StoredHandicapLookup:
    """1レースの出走馬の前走・前々走（``PreviousRunRepository``）を、``ReviewStore`` の表3で引いて、まとまり X の表にする。

    表3には不利のあった走しか無いので、表3の範囲（``as_of``）の中の走で行が無ければ「不利なし（0）」、範囲の外（まだ回顧を書いていない日）の
    走や前走の無い馬は欠損値。回顧は ``tools/回顧/review.py`` が終わったレースのぶんを書き足す（今週の予想の前に自動で回す）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, store: ReviewStore) -> None:
        self._runs = PreviousRunRepository(con)
        self._store = store

    def of(self, race_id: str, race_date: date, horse_ids: list[str]) -> pd.DataFrame:
        """列は ``race_id``・``horse_id`` と ``PREVIOUS_HANDICAP_NAMES``。1行 = 1頭。"""
        previous = self._runs.read(horse_ids, race_date)
        as_of = self._store.as_of()
        notes = self._notes(previous[names.RACE_ID].tolist() if not previous.empty else [])
        rows = []
        for horse_id in horse_ids:
            mine = previous[previous["horse_id"] == str(horse_id)].sort_values("runs_ago")
            rows.append({names.RACE_ID: race_id, names.HORSE_ID: str(horse_id), **self._columns(mine, notes, as_of)})
        return pd.DataFrame(rows, columns=[names.RACE_ID, names.HORSE_ID, *PREVIOUS_HANDICAP_NAMES])

    def _notes(self, race_ids: list[str]) -> pd.DataFrame:
        if not race_ids:
            return pd.DataFrame(columns=[names.RACE_ID, names.HORSE_ID, *names.DEGREES])
        placeholders = ", ".join("?" for _ in race_ids)
        return self._store.read(names.HORSES_TABLE, f"{names.RACE_ID} IN ({placeholders})", race_ids)

    def _columns(self, mine: pd.DataFrame, notes: pd.DataFrame, as_of: date | None) -> dict[str, float]:
        degrees = [self._degrees(run, notes, as_of) for _, run in mine.iterrows()]
        previous = degrees[0] if degrees else None
        if previous is None:
            return {name: float("nan") for name in PREVIOUS_HANDICAP_NAMES}
        maxima = [max(d.values()) for d in degrees if d is not None and all(v == v for v in d.values())]
        return {
            PREVIOUS_LATE_START: previous[names.LATE_START_DEGREE], PREVIOUS_PACE: previous[names.PACE_DEGREE],
            PREVIOUS_BIAS: previous[names.BIAS_DEGREE],
            PREVIOUS_REVIEW: (float(max(previous.values()) >= 2) if all(v == v for v in previous.values()) else float("nan")),
            PREVIOUS_MAX: max(maxima) if maxima else float("nan"),
        }

    def _degrees(self, run: pd.Series, notes: pd.DataFrame, as_of: date | None) -> dict[str, float] | None:
        """その走の3つの程度。表3に行があればその値、無くても範囲の中なら 0、範囲の外なら欠損値。"""
        found = notes[(notes[names.RACE_ID].astype(str) == run[names.RACE_ID]) & (notes[names.HORSE_ID].astype(str) == run["horse_id"])]
        if not found.empty:
            row = found.iloc[0]
            return {degree: float(row[degree]) for degree in names.DEGREES}
        if as_of is not None and run["race_date"].date() <= as_of:
            return {degree: 0.0 for degree in names.DEGREES}
        return {degree: float("nan") for degree in names.DEGREES}
