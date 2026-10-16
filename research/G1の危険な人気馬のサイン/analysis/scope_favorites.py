"""サインの表から、決めた範囲のレースの人気馬の行を取り出す。"""

from __future__ import annotations

import pandas as pd

from .race_scope import RaceScope

#: 人気馬の範囲（人気馬の予想と同じ。13頭以下なら1〜3番人気、14頭以上なら1〜5番人気）。
_LARGE_FIELD = 14
_SMALL_FIELD_FAVORITES, _LARGE_FIELD_FAVORITES = 3, 5
#: 4着以下（負け）の列の名前。
LOST = "lost"


class ScopeFavorites:
    """サインの表（``SignTableBuilder``）のうち、``scope`` のレース（平地だけ）の人気馬の行を返す。

    ``LOST`` の列（4着以下か競走中止なら 1）と ``year`` の列を足す。``first_year`` より前の年は入れない
    （DB の最初の年は前の走が数えられていないので、2012年から）。
    """

    def __init__(self, scope: RaceScope, first_year: int = 2012) -> None:
        self._scope = scope
        self._first_year = first_year

    def select(self, signs: pd.DataFrame) -> pd.DataFrame:
        limit = signs["field_size"].ge(_LARGE_FIELD).map({True: _LARGE_FIELD_FAVORITES, False: _SMALL_FIELD_FAVORITES})
        year = pd.to_datetime(signs["race_date"]).dt.year
        flat = signs["surface"].ne("障害")
        rows = self._scope.matches(signs["grade_code"]) & flat & signs["popularity"].le(limit) & year.ge(self._first_year)
        chosen = signs[rows].copy()
        chosen[LOST] = (~chosen["finish"].le(3)).astype(int)
        chosen["year"] = year[rows]
        return chosen.reset_index(drop=True)
