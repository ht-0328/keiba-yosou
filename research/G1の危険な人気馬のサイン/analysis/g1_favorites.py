"""サインの表から、G1の人気馬の行を取り出す。"""

from __future__ import annotations

import pandas as pd

#: 平地の G1 のグレードコード。
G1_GRADE = "A"
#: 人気馬の範囲（人気馬の予想と同じ。13頭以下なら1〜3番人気、14頭以上なら1〜5番人気）。
_LARGE_FIELD = 14
_SMALL_FIELD_FAVORITES, _LARGE_FIELD_FAVORITES = 3, 5
#: 4着以下（負け）の列の名前。
LOST = "lost"


class G1Favorites:
    """サインの表（``SignTableBuilder``）のうち、平地の G1 の人気馬で、着順か競走中止の分かる行だけを返す。

    ``LOST`` の列（4着以下か競走中止なら 1）と ``year`` の列を足す。``first_year`` より前の年は入れない
    （DB の最初の年は前の走が数えられていないので、2012年から）。
    """

    def __init__(self, first_year: int = 2012) -> None:
        self._first_year = first_year

    def select(self, signs: pd.DataFrame) -> pd.DataFrame:
        limit = signs["field_size"].ge(_LARGE_FIELD).map({True: _LARGE_FIELD_FAVORITES, False: _SMALL_FIELD_FAVORITES})
        year = pd.to_datetime(signs["race_date"]).dt.year
        rows = signs["grade_code"].eq(G1_GRADE) & signs["popularity"].le(limit) & year.ge(self._first_year)
        chosen = signs[rows].copy()
        chosen[LOST] = (~chosen["finish"].le(3)).astype(int)
        chosen["year"] = year[rows]
        return chosen.reset_index(drop=True)
