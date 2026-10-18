"""年ごとに、その年より前の開催日だけで決まりを選び、その年の成績を足していく（ウォークフォワード）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .buy_rule import BuyRule
from .profit_bootstrap import ProfitBootstrap
from .rule_day_table import HIT_RACES, PAYOUT, POINTS

#: 決まりを選ぶ期間の始まりの年（docs/01 の 5。2016〜2017年は選ぶためだけに使う）。
FIRST_YEAR = 2016
#: 選ぶのに要る、選ぶ期間の当たったレースの数。
MIN_HITS = 30
#: 決まりの選び方。全部のレースに1つの決まり（一律）と、芝ダ × クラスの種類ごと。
UNIFORM, BY_KIND = "一律", "種類ごと"
#: 選ぶ基準。利益の下の端（docs/01 の 4）と、今の本番の決まりを選んだ基準（回収率の下の端・当たり 200回以上。比べる行だけに使う）。
PROFIT, RATE = "利益", "回収率"
RATE_MIN_HITS = 200


@dataclass(frozen=True)
class Choice:
    """ある年・ある種類（一律なら ``全部``）に選んだ決まり（無ければ ``None`` = 買わない）と、選ぶ期間での利益の下の端（円）。"""

    year: int
    group: str
    rule: BuyRule | None
    lower_profit: float


class WalkForwardSelector:
    """``RuleDayTable`` の配列 [決まり, 種類, 開催日, 4] から、``years`` の各年について決まりを選び、その年の開催日ごとの成績を返す。

    選ぶ基準は、選ぶ期間（``FIRST_YEAR``〜前の年）での利益（払戻 − 100円 × 点数）の 90% の幅の下の端がいちばん高い決まり（docs/01 の 4）。
    当たったレースが ``MIN_HITS`` に届かない決まりは選ばない。「種類ごと」で、どの決まりも下の端が 0 以下の種類は買わない。
    """

    def __init__(self, table: np.ndarray, days: Sequence[pd.Timestamp], rules: Sequence[BuyRule], groups: Sequence[str]) -> None:
        self._table = table
        self._years = pd.DatetimeIndex(days).year.to_numpy()
        self._rules = list(rules)
        self._groups = list(groups)

    def run(self, mode: str, years: Sequence[int], criterion: str = PROFIT) -> tuple[np.ndarray, list[Choice]]:
        """（開催日ごとの成績 [開催日, 4]。選んだ年以外は 0, 選んだ決まりの一覧）。``criterion`` が ``RATE`` なら、
        回収率の 90% の幅の下の端で選び、当たったレースが ``RATE_MIN_HITS`` に届かない決まりは選ばない（一律だけで使う）。"""
        result = np.zeros(self._table.shape[2:], dtype=float)
        choices: list[Choice] = []
        for year in years:
            train = np.flatnonzero((self._years >= FIRST_YEAR) & (self._years < year))
            test = self._years == year
            bootstrap = ProfitBootstrap(len(train))
            if mode == UNIFORM:
                at, lower = self._best(self._table.sum(axis=1)[:, train, :], bootstrap, criterion)
                choices.append(Choice(year, "全部", self._rules[at] if at is not None else None, lower))
                if at is not None:
                    result[test] += self._table[at].sum(axis=0)[test]
                continue
            for group_at, group in enumerate(self._groups):
                at, lower = self._best(self._table[:, group_at, train, :], bootstrap, criterion)
                if at is None or lower <= 0:
                    choices.append(Choice(year, group, None, lower))
                    continue
                choices.append(Choice(year, group, self._rules[at], lower))
                result[test] += self._table[at, group_at][test]
        return result, choices

    def _best(self, cells: np.ndarray, bootstrap: ProfitBootstrap, criterion: str) -> tuple[int | None, float]:
        """cells は [決まり, 選ぶ期間の開催日, 4]。（いちばん良い決まりの番号, その下の端）。選べる決まりが無ければ（None, −∞）。"""
        rate = criterion == RATE
        eligible = cells[:, :, HIT_RACES].sum(axis=1) >= (RATE_MIN_HITS if rate else MIN_HITS)
        if not eligible.any():
            return None, float("-inf")
        if rate:
            lower = bootstrap.lower_rate((100.0 * cells[:, :, POINTS]).T, cells[:, :, PAYOUT].T)
        else:
            lower = bootstrap.lower((cells[:, :, PAYOUT] - 100.0 * cells[:, :, POINTS]).T)
        lower[~eligible] = -np.inf
        at = int(np.argmax(lower))
        return at, float(lower[at])
