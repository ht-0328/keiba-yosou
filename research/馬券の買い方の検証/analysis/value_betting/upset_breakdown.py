"""買った買い目を、荒れ具合の予想で切った成績の表。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType, UpsetLevel

from 共通.render import Table

from . import columns as c

_RACE_KEY = [c.WINDOW, c.PART, c.RACE_ID]


class UpsetBreakdown:
    """買い目の表を、レースごとの「いちばん確率の高い荒れ具合」（券種ごと）で分けて、点数・賭け金・払戻・回収率を並べる。
    荒れ具合は表の切り口にだけ使い、買う馬・レースの選び方には使わない（docs/05-round3-protocol.md）。"""

    def table(self, tickets: pd.DataFrame, races: pd.DataFrame, title: str) -> Table:
        columns = ["券種", "荒れ具合", "点数", "賭け金（円）", "払戻（円）", "回収率"]
        if tickets.empty:
            return Table(columns, [], title=title)
        level_columns = [c.upset_level_column(bet) for bet in BetType]
        joined = tickets.merge(races[_RACE_KEY + level_columns], on=_RACE_KEY, how="left")
        rows = [row for bet in BetType for row in self._rows(joined, bet)]
        return Table(columns, rows, title=title, note="荒れ具合 = その券種で、荒れ具合の予想がいちばん高い確率を付けた段階。表の切り口にだけ使う。")

    def _rows(self, joined: pd.DataFrame, bet: BetType) -> list[list[object]]:
        column = c.upset_level_column(bet)
        grouped = joined.groupby(joined[column].fillna("予想なし"))
        order = [*UpsetLevel.labels(), "予想なし"]
        rows = []
        for label in order:
            if label not in grouped.groups:
                continue
            group = grouped.get_group(label)
            stake, payout = int(group[c.STAKE_YEN].sum()), int(group[c.PAYOUT_YEN].sum())
            rows.append([bet.label, label, len(group), stake, payout, f"{payout / stake:.1%}" if stake else ""])
        return rows
