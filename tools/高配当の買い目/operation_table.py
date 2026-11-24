"""運用の目安の表（表4）。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from 共通.render import Table

from 今週の予想.ticket_rules import POINT_YEN

from 高配当の買い目.number_text import number_text, rate_text, signed_yen_text, yen_text
from 高配当の買い目.pick_groups import PickGroups
from 高配当の買い目.pick_numbers import PickNumbers
from 高配当の買い目.race_universe import RaceUniverse

COLUMNS: tuple[str, ...] = ("券種", "1開催日の買うレース", "1開催日の点数", "1開催日の金額", "1年の投資", "1年の収支", "いちばん深い落ち込み",
                            "外れが続いた最長のレース数", "高配当が1本以上当たった開催日の割合", "1開催日の的中の平均")


class OperationTable:
    """券種ごと（最後に合計）の、買い続けるときの目安の表（1点 ``POINT_YEN`` 円）。

    1開催日あたり・開催日の割合の分母は ``universe`` の開催日の数（買い目の無かった開催日も数える）、1年あたりの分母は ``universe`` の期間の長さ（年）。
    落ち込みと外れ続きの数え方は ``PickNumbers.drawdown``・``PickNumbers.longest_miss``。
    """

    def __init__(self, universe: RaceUniverse, groups: PickGroups) -> None:
        self._universe = universe
        self._groups = groups

    def table(self, picks: pd.DataFrame, note: str) -> Table:
        rows = [self._row(label, PickNumbers(group)) for label, group in self._groups.of(picks)]
        return Table(list(COLUMNS), rows, title=f"4. 運用の目安（1点 {POINT_YEN}円）", note=note)

    def _row(self, label: str, numbers: PickNumbers) -> list[Any]:
        days, years = self._universe.day_count, self._universe.year_span
        return [label, number_text(_per(numbers.races, days)), number_text(_per(numbers.points, days)), yen_text(_per(numbers.stake, days)),
                yen_text(_per(numbers.stake, years)), signed_yen_text(_per(numbers.payout - numbers.stake, years)), yen_text(numbers.drawdown()),
                f"{numbers.longest_miss():,}", rate_text(_per(numbers.hit_days(), days)), number_text(_per(numbers.hits, days), 2)]


def _per(value: float, base: float) -> float:
    """``value`` ÷ ``base``。分母が 0 なら欠損値。"""
    return value / base if base else float("nan")
