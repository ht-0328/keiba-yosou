"""本線だけ・本線＋抑え・抑えだけの、年ごとの成績の表。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_win5_tickets.settlement import HIT, PAYOUT, RACE_DATE, STAKE, STRATEGY

from .hedge_day_bets import COVERED, LONGSHOT_LEGS, WIN_PAYOUT
from .hedge_summary import BIG_PAYOUT, HUGE_PAYOUT


@dataclass(frozen=True)
class HedgeYearTable:
    """1行 = 1つの買い方 × 1年。"""

    def build(self, settled: pd.DataFrame, strategies: Sequence[str], title: str) -> Table:
        years = sorted(settled[RACE_DATE].str[:4].unique())
        rows = [self._row(name, year, settled) for name, year in product(strategies, years)]
        return Table(["買い方", "年", "買った日数", "代金", "払戻", "回収率", "当たった回数", "的中率", "100万円以上の的中", "1,000万円以上の的中",
                      "人気薄が勝ったレース", "そのうち買い目に入っていた"], rows, title=title)

    @staticmethod
    def _row(name: str, year: str, settled: pd.DataFrame) -> list[object]:
        part = settled.loc[(settled[STRATEGY] == name) & (settled[RACE_DATE].str[:4] == year)]
        stake, payout, hits = int(part[STAKE].sum()), int(part[PAYOUT].sum()), int(part[HIT].sum())
        recovery = f"{payout / stake:.1%}" if stake else "―"
        rate = f"{hits / len(part):.1%}" if len(part) else "―"
        return [name, year, len(part), f"{stake:,}円", f"{payout:,}円", recovery, hits, rate, int((part[WIN_PAYOUT] >= BIG_PAYOUT).sum()),
                int((part[WIN_PAYOUT] >= HUGE_PAYOUT).sum()), int(part[LONGSHOT_LEGS].sum()), int(part[COVERED].sum())]
