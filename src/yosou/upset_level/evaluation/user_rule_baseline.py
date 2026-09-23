"""利用者の規則を、比べる基準として測る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import FAVORITE_ODDS, UPPER_MAX_ODDS, TrainingData
from yosou.shared.feature import as_numbers

from ..dataset.upset_level import UpsetLevel
from .user_rule_result import UserRuleResult

#: 利用者の規則の線（1番人気のオッズがこれ以上、2〜5番人気の最大オッズがこれ未満なら荒れる）。
FAVORITE_ODDS_FROM = 4.0
UPPER_ODDS_BELOW = 10.0


class UserRuleBaseline:
    """利用者の規則（1番人気 4.0倍以上かつ 2〜5番人気の最大オッズ 10倍未満）を「中荒れ以上」の予想とみなして、
    的中率と再現率を出す（設計書 16 の 3）。モデルによらない基準で、モデルの「中荒れ以上の確率」と比べる。

    規則は評価用の列（1番人気の確定オッズ・2〜5番人気の最大の確定オッズ）から作り、特徴量にはしない（設計書 15 の 9）。
    """

    def applies(self, evaluation: pd.DataFrame) -> pd.Series:
        """レースごとに、規則に当てはまるか。オッズが無ければ False。"""
        favorite = as_numbers(evaluation[FAVORITE_ODDS])
        upper = as_numbers(evaluation[UPPER_MAX_ODDS])
        return (favorite >= FAVORITE_ODDS_FROM) & (upper < UPPER_ODDS_BELOW)

    def evaluate(self, data: TrainingData) -> UserRuleResult:
        """``data`` の目的変数（その券種の荒れ具合）に対する、規則の当たり具合。"""
        hit = self.applies(data.evaluation).to_numpy()
        is_upset = (data.label.to_numpy() >= UpsetLevel.MID.value)
        return UserRuleResult(
            rows=int(len(data)),
            hits=int(hit.sum()),
            precision=self._share(is_upset[hit]),
            recall=self._share(hit[is_upset]),
            base_rate=self._share(is_upset),
        )

    def _share(self, flags: np.ndarray) -> float:
        """真の割合。要素が無ければ NaN。"""
        if len(flags) == 0:
            return float("nan")
        return float(flags.mean())
