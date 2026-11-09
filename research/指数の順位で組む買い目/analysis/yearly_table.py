"""形ごとの年ごとの回収率と的中率の表。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from 共通.perf import percent
from 共通.render import Table

from .member_races import MemberRaces
from .payout_table import PAYOUT
from .period_table import POINT_YEN
from .row_spec import RowSpec
from .ticket_settlement import HIT, POINTS


class YearlyTable:
    """精算の表から、行（``RowSpec``）× 年の 回収率の表と的中率の表を作る（1点 100円）。買っていない年は —。"""

    def __init__(self, specs: Sequence[RowSpec]) -> None:
        self._specs = list(specs)
        self._members = MemberRaces()

    def tables(self, settled: pd.DataFrame, title_head: str) -> list[Table]:
        years = sorted(pd.to_datetime(settled["race_date"]).dt.year.unique().tolist())
        recovery_rows, hit_rows = [], []
        for spec in self._specs:
            races = self._members.of(settled, spec)
            by_year = self._by_year(races)
            recovery_rows.append([spec.label, spec.ticket, *[self._recovery(by_year, year) for year in years]])
            hit_rows.append([spec.label, spec.ticket, *[self._hit_rate(by_year, year) for year in years]])
        headers = ["形", "券種", *[str(year) for year in years]]
        return [Table(headers, recovery_rows, title=f"{title_head} 年ごとの回収率", note="1点 100円。買っていない年は —。"),
                Table(headers, hit_rows, title=f"{title_head} 年ごとの的中率（買ったレースのうち当たったレースの割合）",
                      note="買ったレース = 形に1点以上あったレース。")]

    @staticmethod
    def _by_year(races: pd.DataFrame) -> pd.DataFrame:
        if races.empty:
            return pd.DataFrame(columns=[POINTS, PAYOUT, HIT, "races"])
        grouped = races.groupby(pd.to_datetime(races["race_date"]).dt.year)
        return grouped.agg(**{POINTS: (POINTS, "sum"), PAYOUT: (PAYOUT, "sum"), HIT: (HIT, "sum"), "races": ("race_id", "size")})

    @staticmethod
    def _recovery(by_year: pd.DataFrame, year: int) -> str:
        if year not in by_year.index or by_year.loc[year, POINTS] <= 0:
            return "—"
        return percent(float(by_year.loc[year, PAYOUT]) / (float(by_year.loc[year, POINTS]) * POINT_YEN))

    @staticmethod
    def _hit_rate(by_year: pd.DataFrame, year: int) -> str:
        if year not in by_year.index or by_year.loc[year, "races"] <= 0:
            return "—"
        return percent(float(by_year.loc[year, HIT]) / float(by_year.loc[year, "races"]))
