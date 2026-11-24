"""学習の行を作る（外れの組を間引いて、重みを付ける）。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from .column_names import HIT, WEIGHT
from .miss_keep_rates import MISS_KEEP_RATES, SEED_BASE


class MissSampling:
    """1年ぶんの組の表から、学習の行を選ぶ。当たりの組は全部残し、外れの組は券種ごとの割合で間引く。

    残した外れの行には重み 1 ÷ 割合 を付ける（当たりは 1）。重みを掛けると、間引く前と同じ当たりの割合になる。
    例: 3連複（割合 0.06）で外れが 10万行なら、約 6,000行を残して重み 16.7 を付ける。
    乱数の種は年ごとに固定（``SEED_BASE`` ＋ 年）なので、同じ表からは毎回同じ行が残る。
    """

    def __init__(self, keep_rates: Mapping[TicketType, float] = MISS_KEEP_RATES) -> None:
        self._keep_rates = keep_rates

    def sample(self, ticket_type: TicketType, table: pd.DataFrame, year: int) -> pd.DataFrame:
        """``table`` に重みの列（``weight``）を足した、学習の行だけの表。行の並びは元のまま、index は振り直す。"""
        rate = self._keep_rates[ticket_type]
        is_hit = table[HIT].to_numpy() == 1
        random = np.random.default_rng(SEED_BASE + year)
        is_kept = is_hit | (random.random(len(table)) < rate)
        weight = np.where(is_hit, 1.0, 1.0 / rate)
        return table.assign(**{WEIGHT: weight})[is_kept].reset_index(drop=True)
