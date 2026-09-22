"""予測に使う単勝オッズを、出走の行に反映する。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from ..feature import as_numbers


class AnnouncedOddsApplier:
    """渡された「馬番 → 単勝オッズ」がある馬は、単勝オッズ（``win_odds``）をその値にする。無い馬は、出走の行の値のまま。

    渡すのは、利用者が手で入れたオッズか、締め切り前のオッズ（時系列オッズ）から作ったもの。
    終わったレースを予測し直すときは何も渡されず、出走の行に入っている確定オッズがそのまま使われる。
    """

    def apply(self, entries: pd.DataFrame, odds: Mapping[int, float] | None) -> pd.DataFrame:
        """``odds`` が無ければ ``entries`` をそのまま返す。行の並びと index は変えない。"""
        if not odds:
            return entries
        by_horse_no = {float(horse_no): float(value) for horse_no, value in odds.items()}
        given = as_numbers(entries["horse_no"]).map(by_horse_no)
        current = as_numbers(entries["win_odds"])
        return entries.assign(win_odds=current.mask(given.notna(), given))
