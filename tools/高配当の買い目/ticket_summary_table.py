"""券種ごとの成績の表（表1）。"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from 共通.render import Table

from 高配当の買い目.number_text import BLANK, number_text, rate_text
from 高配当の買い目.pick_groups import PickGroups
from 高配当の買い目.pick_numbers import PickNumbers
from 高配当の買い目.race_universe import RaceUniverse

COLUMNS: tuple[str, ...] = ("券種", "買ったレース", "全レースに対する割合", "1レースの点数", "点数", "的中数", "的中したレースの割合",
                            "当たったときの配当（倍）の中央", "回収率", "回収率の90%の幅")


class TicketSummaryTable:
    """券種ごと（最後に合計）の、買ったレース・点数・的中・配当・回収率の表。

    全レースに対する割合の分母は ``universe``（買わなかったレースも含む全部のレース）。回収率の 90% の幅は、開催日を単位にしたブートストラップ。
    """

    def __init__(self, universe: RaceUniverse, groups: PickGroups) -> None:
        self._universe = universe
        self._groups = groups

    def table(self, picks: pd.DataFrame, note: str) -> Table:
        rows = [self._row(label, PickNumbers(group)) for label, group in self._groups.of(picks)]
        return Table(list(COLUMNS), rows, title="1. 券種ごとの成績", note=note)

    def _row(self, label: str, numbers: PickNumbers) -> list[Any]:
        share = numbers.races / self._universe.race_count if self._universe.race_count else float("nan")
        low, high = numbers.interval()
        interval = BLANK if math.isnan(low) else f"{rate_text(low)}〜{rate_text(high)}"
        return [label, f"{numbers.races:,}", rate_text(share), number_text(numbers.points_per_race), f"{numbers.points:,}", f"{numbers.hits:,}",
                rate_text(numbers.hit_race_share), number_text(numbers.median_multiple), rate_text(numbers.rate), interval]
