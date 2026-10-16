"""回顧の不利を読む。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from yosou.review import names
from yosou.review.repository.review_store import ReviewStore

#: 不利の種類と、その程度の列。
KINDS: tuple[tuple[str, str], ...] = (
    (names.LATE_START, names.LATE_START_DEGREE), (names.PACE_AGAINST, names.PACE_DEGREE), (names.BIAS_AGAINST, names.BIAS_DEGREE),
)
COLUMNS: tuple[str, ...] = (names.RACE_ID, names.HORSE_ID, *(degree for _, degree in KINDS))


class ReviewNoteRepository:
    """回顧の表3「馬の回顧ノート」（``reports/回顧/review.duckdb``）から、対象の走の不利の種類と程度を読む。

    回顧のファイルがまだ無ければ空（不利は無いものとして文を作る）。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store

    def read(self, race_ids: Sequence[str], horse_ids: Sequence[str]) -> pd.DataFrame:
        """列は ``COLUMNS``。1行 = 不利のあった1走。"""
        if not race_ids or not horse_ids or not self._store.path.exists():
            return pd.DataFrame(columns=list(COLUMNS))
        race_marks = ", ".join("?" for _ in race_ids)
        horse_marks = ", ".join("?" for _ in horse_ids)
        where = f'"{names.RACE_ID}" IN ({race_marks}) AND "{names.HORSE_ID}" IN ({horse_marks})'
        frame = self._store.read(names.HORSES_TABLE, where, [*race_ids, *horse_ids])
        return frame[list(COLUMNS)].assign(**{names.RACE_ID: frame[names.RACE_ID].astype(str), names.HORSE_ID: frame[names.HORSE_ID].astype(str)})

    def words_of(self, row: pd.Series) -> tuple[str, ...]:
        """1行を ``出遅れ（中）`` の形の言葉にする（程度が 1 以上の種類だけ）。"""
        words = []
        for kind, column in KINDS:
            degree = pd.to_numeric(row.get(column), errors="coerce")
            if pd.notna(degree) and int(degree) >= 1:
                words.append(f"{kind}（{names.DEGREE_NAMES[int(degree)]}）")
        return tuple(words)
