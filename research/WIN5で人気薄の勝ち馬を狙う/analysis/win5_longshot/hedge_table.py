"""買い方の成績（``HedgeSummary`` の表）を、見せる表にする。"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_win5_tickets.settlement import PAYOUT, STAKE, STRATEGY

from 印の成績.win5_strategy_summary import DAYS, HIGH, HIT_RATE, HITS, LOW, RECOVERY

from .hedge_day_bets import COVERED, LONGSHOT_LEGS
from .hedge_summary import BIG, COVERAGE, HUGE

_COLUMNS = ["買い方", "買った日数", "代金の合計", "払戻の合計", "回収率", "当たった回数", "的中率", "回収率の 90% の幅", "100万円以上の的中",
            "1,000万円以上の的中", "人気薄が勝ったレース", "そのうち買い目に入っていた", "人気薄の勝ち馬を含めた割合"]


@dataclass(frozen=True)
class HedgeTable:
    """``order`` を渡すと、その買い方だけをその順に並べる。"""

    def build(self, summary: pd.DataFrame, title: str, order: Sequence[str] | None = None, note: str = "") -> Table:
        rows = summary.set_index(STRATEGY)
        names = [name for name in (order or list(rows.index)) if name in rows.index]
        return Table(_COLUMNS, [self._row(name, rows.loc[name]) for name in names], title=title, note=note)

    @staticmethod
    def _row(name: str, row: pd.Series) -> list[object]:
        return [
            name, int(row[DAYS]), f"{int(row[STAKE]):,}円", f"{int(row[PAYOUT]):,}円", _percent(row[RECOVERY]), int(row[HITS]),
            _percent(row[HIT_RATE]), f"{_percent(row[LOW])}〜{_percent(row[HIGH])}", int(row[BIG]), int(row[HUGE]),
            int(row[LONGSHOT_LEGS]), int(row[COVERED]), _percent(row[COVERAGE]),
        ]


def _percent(value: object) -> str:
    number = float(value)
    return "―" if math.isnan(number) else f"{number:.1%}"
