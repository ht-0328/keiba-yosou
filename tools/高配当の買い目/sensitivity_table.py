"""期待値の線と上限の点数を動かしたときの回収率の表（表5）。"""

from __future__ import annotations

from itertools import chain, product
from typing import Any

import pandas as pd

from 共通.render import Table

from 高配当の買い目.backtest_picks import BacktestPicks
from 高配当の買い目.number_text import rate_text
from 高配当の買い目.pick_columns import SENSITIVITY_MAX_POINTS, SENSITIVITY_VALUE_LINES
from 高配当の買い目.pick_groups import PickGroups
from 高配当の買い目.pick_numbers import PickNumbers
from 高配当の買い目.search_verify_periods import SearchVerifyPeriods

#: 上限の点数が無いときのセル。
NO_CAP = "なし"


class SensitivityTable:
    """期待値の線（``SENSITIVITY_VALUE_LINES``）× 1レース1券種の上限の点数（``SENSITIVITY_MAX_POINTS``）ごとに買い目を選び直して、
    券種ごと（最後に合計）の 点数・的中数 と、探す期間・確かめる期間・全体の回収率 を並べる。

    線を少し動かしただけで成績が大きく変わらないか（たまたまその線で良く見えただけでないか）を見る表。買い目は ``BacktestPicks.select`` で、
    候補（いちばん低い線・上限なしで選んだ組）から選び直す。
    """

    def __init__(self, backtest: BacktestPicks, groups: PickGroups, periods: SearchVerifyPeriods) -> None:
        self._backtest = backtest
        self._groups = groups
        self._periods = periods

    def table(self, candidates: pd.DataFrame, note: str) -> Table:
        columns = ["期待値の線", "上限の点数", "券種", "点数", "的中数", f"{self._periods.search_label}の回収率",
                   f"{self._periods.verify_label}の回収率", "全体の回収率"]
        by_rule = [self._rows(candidates, value_line, max_points)
                   for value_line, max_points in product(SENSITIVITY_VALUE_LINES, SENSITIVITY_MAX_POINTS)]
        rows = list(chain.from_iterable(by_rule))
        return Table(columns, rows, title="5. 線の感度（期待値の線と上限の点数を動かしたとき）", note=note)

    def _rows(self, candidates: pd.DataFrame, value_line: float, max_points: int | None) -> list[list[Any]]:
        picks = self._backtest.select(candidates, value_line, max_points)
        head = [f"{value_line:.2f}", NO_CAP if max_points is None else str(max_points)]
        return [[*head, label, *self._cells(group)] for label, group in self._groups.of(picks)]

    def _cells(self, picks: pd.DataFrame) -> list[str]:
        numbers = PickNumbers(picks)
        by_period = [rate_text(PickNumbers(part).rate) for _, part in self._periods.split(picks)]
        return [f"{numbers.points:,}", f"{numbers.hits:,}", *by_period, rate_text(numbers.rate)]
