"""3連単の組ごとの確率を足し合わせて、ほかの券種の組の確率にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..betting import TicketType
from .combo_columns import horse_columns

#: 2頭の券種のうち、3連単の組の1・2頭目を足す券種（着順を区別する馬単と、並びを無視する馬連）。ワイドは3連複から作る。
_TOP_TWO = (TicketType.EXACTA, TicketType.QUINELLA)


class PoolFolding:
    """3連単の組ごとの確率の列（``TrifectaSources.of`` の ``market``・``harville``）を、券種の組ごとに足し合わせる。

    i→j→k の確率を t とすると、馬単 i→j は t の k についての合計、馬連 i-j は馬単 i→j と j→i の和、
    3連複 i-j-k は6つの並びの和、ワイド i-j は3連複 i-j-k の k についての合計（i と j がどちらも3着以内）。
    順不同の券種の組は、馬番の小さい順にそろえる（元DB の組番と同じ）。戻り値の列は ``race_id``・``h1``…・確率の列。
    """

    def fold(self, ticket_type: TicketType, trifecta: pd.DataFrame, values: list[str]) -> pd.DataFrame:
        if ticket_type is TicketType.TRIFECTA:
            return trifecta[["race_id", *horse_columns(3), *values]]
        if ticket_type in _TOP_TWO:
            return self._top_two(ticket_type, trifecta, values)
        trio = self._sorted_sum(trifecta, horse_columns(3), values)
        if ticket_type is TicketType.TRIO:
            return trio
        if ticket_type is TicketType.WIDE:
            return self._wide(trio, values)
        raise ValueError(f"3連単から作れない券種です: {ticket_type.label}")

    def _top_two(self, ticket_type: TicketType, trifecta: pd.DataFrame, values: list[str]) -> pd.DataFrame:
        exacta = trifecta.groupby(["race_id", "h1", "h2"], sort=False)[values].sum().reset_index()
        if ticket_type is TicketType.EXACTA:
            return exacta
        return self._sorted_sum(exacta, horse_columns(2), values)

    def _wide(self, trio: pd.DataFrame, values: list[str]) -> pd.DataFrame:
        pairs = [trio[["race_id", first, second, *values]].set_axis(["race_id", "h1", "h2", *values], axis=1)
                 for first, second in (("h1", "h2"), ("h1", "h3"), ("h2", "h3"))]
        return pd.concat(pairs, ignore_index=True).groupby(["race_id", "h1", "h2"], sort=False)[values].sum().reset_index()

    def _sorted_sum(self, frame: pd.DataFrame, names: list[str], values: list[str]) -> pd.DataFrame:
        """組の馬番を小さい順に並べ替えてから、同じ組を足す。"""
        ordered = np.sort(frame[names].to_numpy(dtype=int), axis=1)
        sorted_frame = frame[["race_id", *values]].assign(**{name: ordered[:, at] for at, name in enumerate(names)})
        return sorted_frame.groupby(["race_id", *names], sort=False)[values].sum().reset_index()
