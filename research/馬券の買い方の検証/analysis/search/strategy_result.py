"""戦略の評価の結果。"""

from __future__ import annotations

from dataclasses import dataclass

from ..summary import ReturnSummary
from .strategy import Strategy


@dataclass(frozen=True)
class StrategyResult:
    """1つの戦略を、ある期間のレースで評価した結果。

    - ``race_count``: 期間のレース数。``wide_races``・``narrow_races``: 広め・少点数で買うと決めたレース数。``selected_races``: どちらかで買うレース数。
    - ``total``: 全体のまとめ（レース単位に広めと少点数を足してから集計）。``wide``・``narrow``: それぞれのまとめ（使わなければ None）。
    - ``by_month``: 月（``YYYY-MM``）ごとのまとめ。
    """

    strategy: Strategy
    race_count: int
    wide_races: int
    narrow_races: int
    selected_races: int
    total: ReturnSummary
    wide: ReturnSummary | None
    narrow: ReturnSummary | None
    by_month: dict[str, ReturnSummary]

    @property
    def return_rate(self) -> float | None:
        return self.total.return_rate

    @property
    def monthly_rates(self) -> list[float]:
        """買った月の回収率の並び（採否の基準の「月別の中央値」に使う）。"""
        return [summary.return_rate for summary in self.by_month.values() if summary.return_rate is not None]
