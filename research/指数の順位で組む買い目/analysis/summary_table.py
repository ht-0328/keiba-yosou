"""形ごとに、探索と確認の回収率・的中率を1行に並べた要約の表（docs に貼る形）。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from 共通.perf import percent
from 共通.render import Table

from .member_races import MemberRaces
from .payout_table import PAYOUT
from .period import Period
from .period_table import POINT_YEN
from .row_spec import RowSpec
from .ticket_settlement import HIT, POINTS


class SummaryTable:
    """精算の表から、行（``RowSpec``）ごとに 1レースの点数と金額、期間ごとの回収率と的中率、集計金額を満たした的中の割合（全期間）を
    1行に並べる。実額は出さない（docs に貼る）。期間に買ったレースが無ければ —。"""

    def __init__(self, specs: Sequence[RowSpec], periods: Sequence[Period]) -> None:
        self._specs = list(specs)
        self._periods = list(periods)
        self._members = MemberRaces()

    def table(self, settled: pd.DataFrame, title: str, note: str = "") -> Table:
        headers = ["形", "券種", "1レースの点数", "1レースの金額"]
        for period in self._periods:
            headers += [f"{period.label} 回収率", f"{period.label} 的中率"]
        headers.append("集計金額を満たした的中の割合（全期間）")
        rows = []
        for spec in self._specs:
            races = self._members.of(settled, spec)
            if races.empty:
                continue
            years = pd.to_datetime(races["race_date"]).dt.year
            row = [spec.label, spec.ticket, f"{races[POINTS].sum() / len(races):.1f}", f"{races[POINTS].sum() / len(races) * POINT_YEN:,.0f}円"]
            for period in self._periods:
                chosen = races[period.contains(years)]
                row += self._rates(chosen)
            row.append(self._floor_share(spec, races))
            rows.append(row)
        return Table(headers, rows, title=title, note=note)

    @staticmethod
    def _rates(races: pd.DataFrame) -> list[str]:
        if races.empty:
            return ["—", "—"]
        return [percent(float(races[PAYOUT].sum()) / (float(races[POINTS].sum()) * POINT_YEN)), percent(float(races[HIT].sum()) / len(races))]

    @staticmethod
    def _floor_share(spec: RowSpec, races: pd.DataFrame) -> str:
        hits = races[races[HIT]]
        if not spec.floors or hits.empty:
            return "—"
        parts = []
        for floor in spec.floors:
            floors = hits[POINTS].astype(int).map(floor.of)
            parts.append(f"{percent(float((hits[PAYOUT] >= floors).mean()))}（{floor.label}）")
        return " ／ ".join(parts)
