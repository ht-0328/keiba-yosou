"""印を付けた表から、馬ごとの表に残す行と列を選ぶ。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from 高配当の買い目.horse_table_columns import EXTRA_COLUMNS, KEY_COLUMNS, RACE_DATE, RACE_ID, REQUIRED_COLUMNS


class HorseTableSelector:
    """印を付けた表（``HorseMarker.mark`` の戻り値。1行 = 1頭）から、馬ごとの表に残す行（開催日の範囲）と列を選ぶ。

    列は ``REQUIRED_COLUMNS``（無ければ誤り）と、あれば ``EXTRA_COLUMNS``。``race_id`` は文字列、``race_date`` は日付（時刻なし）にそろえ、
    レースID・馬番の順に並べる。同じ (race_id, horse_no) が2行あれば誤りにする（予想のパッケージが読むときの約束）。
    例: 2026-07-01 〜 2026-09-22 を残すなら ``HorseTableSelector(date(2026, 7, 1), date(2026, 9, 22))``。範囲を省くと全部の行。
    """

    def __init__(self, first_day: date | None = None, last_day: date | None = None) -> None:
        self._first_day = first_day
        self._last_day = last_day

    def select(self, marked: pd.DataFrame) -> pd.DataFrame:
        missing = [column for column in REQUIRED_COLUMNS if column not in marked.columns]
        if missing:
            raise ValueError(f"印を付けた表に、馬ごとの表に要る列がありません: {', '.join(missing)}")
        columns = [*REQUIRED_COLUMNS, *(column for column in EXTRA_COLUMNS if column in marked.columns)]
        table = marked[columns].assign(**{RACE_ID: marked[RACE_ID].astype(str), RACE_DATE: pd.to_datetime(marked[RACE_DATE]).dt.normalize()})
        table = table[self.in_range(table[RACE_DATE])]
        if table.duplicated(list(KEY_COLUMNS)).any():
            raise ValueError("同じレース・同じ馬番の行が2つあります（予測のファイルに同じ出走が重なっている）")
        return table.sort_values(list(KEY_COLUMNS), kind="stable").reset_index(drop=True)

    def in_range(self, days: pd.Series) -> pd.Series:
        """開催日が残す範囲に入るか（真偽）。端を省いた側は絞らない。"""
        days = pd.to_datetime(days)
        kept = pd.Series(True, index=days.index)
        if self._first_day is not None:
            kept &= days >= pd.Timestamp(self._first_day)
        if self._last_day is not None:
            kept &= days <= pd.Timestamp(self._last_day)
        return kept
