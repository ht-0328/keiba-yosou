"""買い目の確定オッズを（券種・レース・組番）で覚えておき、まだ無い組だけ元DB から読む。"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from yosou.shared.betting import ticket_kind
from yosou.shared.repository.ticket_odds_repository import TicketOddsRepository

from 今週の予想.mark_tickets import ODDS


class OddsCache:
    """道具「印の成績」の ``TicketPayouts`` と同じ確定オッズ（複勝・ワイドは最低オッズ。無投票・取消の組は欠損値）を、
    券種ごとに（レースID・組番）→ オッズ で覚えておく。一度読んで無かった組も覚えて、二度は読まない。

    ``attach`` は買い目の表に列 ``odds`` を付ける（トリガミの確かめに使う）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con
        self._known: dict[str, pd.Series] = {}

    def attach(self, tickets: pd.DataFrame) -> pd.DataFrame:
        if tickets.empty:
            return tickets.assign(**{ODDS: pd.Series(dtype=float)})
        parts = []
        for label, group in tickets.groupby("ticket_type", sort=False):
            wanted = pd.MultiIndex.from_frame(group[["race_id", "combo"]].astype(str).drop_duplicates())
            known = self._fill(label, wanted)
            index = pd.MultiIndex.from_frame(group[["race_id", "combo"]].astype(str))
            parts.append(group.assign(**{ODDS: known.reindex(index).to_numpy()}))
        return pd.concat(parts, ignore_index=True)

    def _fill(self, label: str, wanted: pd.MultiIndex) -> pd.Series:
        """``wanted`` の組を全部覚えた状態の、その券種のオッズ（index は（レースID, 組番））。"""
        known = self._known.get(label)
        missing = wanted if known is None else wanted[~wanted.isin(known.index)]
        if len(missing):
            asked = pd.DataFrame({"race_id": missing.get_level_values(0), "combo": missing.get_level_values(1)})
            found = TicketOddsRepository(self._con, ticket_kind(label)).read(asked)
            fetched = pd.Series(np.nan, index=missing, dtype=float)
            if not found.empty:
                values = found.set_index(["race_id", "combo"])["odds"].astype(float)
                values = values[~values.index.duplicated()]
                fetched.update(values)
            known = fetched if known is None else pd.concat([known, fetched])
            self._known[label] = known
        return known
