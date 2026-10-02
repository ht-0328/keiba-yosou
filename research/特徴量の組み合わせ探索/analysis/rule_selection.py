"""ルールの採否。基準は結果を見る前に決めて、ここだけに書く。"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .roi_scan import PERIODS

#: ルールを区別する列。
RULE_KEYS = ["区分の段", "区分", "人気帯", "特徴量", "馬の条件"]
#: YAML に書くための値（区分と人気帯と馬の条件の中身）。
RULE_VALUES = ["区分の条件", "人気の範囲", "馬の条件の値"]
BET_TYPES = ("単勝", "複勝")


@dataclass(frozen=True)
class RuleSelection:
    """見つける期間で回収率が ``discover_rate`` 以上（点数 ``discover_bets`` 以上）のルールを候補にし、
    確かめる期間でも ``confirm_rate`` 以上（点数 ``confirm_bets`` 以上）なら採用する。テスト期間は採否に使わず、
    採用したルールが続いたかを1回だけ見る。
    """

    discover_bets: int = 300
    discover_rate: float = 1.10
    confirm_bets: int = 100
    confirm_rate: float = 1.00

    def wide(self, counts: pd.DataFrame, bet: str) -> pd.DataFrame:
        """ルールごとに、期間ごとの点数・的中率・回収率・標準誤差から見た100%との差（z）を横に並べる。"""
        values = counts.drop_duplicates(RULE_KEYS).set_index(RULE_KEYS)[RULE_VALUES]
        table = counts.set_index([*RULE_KEYS, "期間"])
        bets = table["点数"]
        mean = table[f"{bet}払戻"] / bets
        variance = (table[f"{bet}払戻2乗"] / bets - mean ** 2).clip(lower=0)
        standard_error = np.sqrt(variance / bets)
        per_period = pd.DataFrame({
            "点数": bets, "的中率": table[f"{bet}的中"] / bets, "回収率": mean,
            "z": (mean - 1) / standard_error.replace(0, np.nan),
        }).unstack("期間")
        per_period.columns = [f"{period}_{name}" for name, period in per_period.columns]
        columns = [f"{period}_{name}" for period in PERIODS for name in ("点数", "的中率", "回収率", "z")]
        return per_period.reindex(columns=columns).join(values).reset_index()

    def candidates(self, wide: pd.DataFrame) -> pd.DataFrame:
        found = (wide["見つける_点数"] >= self.discover_bets) & (wide["見つける_回収率"] >= self.discover_rate)
        return wide[found]

    def adopted(self, wide: pd.DataFrame) -> pd.DataFrame:
        found = self.candidates(wide)
        confirmed = (found["確かめる_点数"] >= self.confirm_bets) & (found["確かめる_回収率"] >= self.confirm_rate)
        return found[confirmed].sort_values("確かめる_回収率", ascending=False)
