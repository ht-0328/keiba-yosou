"""能力指数と今回の斤量から、能力スコアとレース内の位置の列を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.race_development.feature.race_order import RaceOrder
from yosou.race_development.feature.race_order_statistic import RaceOrderStatistic

from .features import DEVIATION, GAP_TO_SECOND, RANK, SCORE

#: 能力指数の元の列（馬の力の材料 M の「指数_条件の重み」。近8走のスピード指数を、新しさと今回の条件への近さで重み付けした平均）と、今回の斤量の列。
ABILITY_INDEX = "指数_条件の重み"
CARRIED = "carried"
#: 斤量 1kg あたりの点数（スピード指数は 1kg = 0.05% で 55kg にそろえてあり、1% = 10点なので 0.5点）と、そろえる斤量。
POINTS_PER_KG = 0.5
BASE_CARRIED_KG = 55.0


class AbilityScoreColumns:
    """設計書「買うレースと買い目を決める」04 の式で、出走ごとに4つの列を作る。

    - 能力スコア = 能力指数 − 0.5 ×（今回の斤量 − 55kg）。スピード指数は 55kg にそろえてあるので、今回の斤量の分だけ引く
    - 偏差 = （能力スコア − レースの平均）÷ レースの標準偏差
    - 2位との差 = 能力スコア − 自分を除いたレースの最高（1位の馬は2位との差で正、ほかの馬は1位との差で負か 0）
    - 順位 = レース内で高い順（1 がいちばん高い。同じ値は同じ順位）

    能力指数か斤量の無い馬（新馬など）は4つとも欠損値。1頭しかいないレースの偏差は欠損値。
    例（架空）: 能力指数 83.0 で 58kg なら、能力スコアは 83.0 − 1.5 = 81.5。16頭の平均 78.0・標準偏差 3.0 なら偏差は 1.17。
    """

    def of(self, features: pd.DataFrame, race_ids: pd.Series) -> pd.DataFrame:
        """``features``（能力指数と斤量の列を持つ）と同じ index の、4列の表。"""
        score = self._score(features)
        race = pd.Series(race_ids.astype(str).to_numpy(), index=features.index)
        grouped = score.groupby(race)
        return pd.DataFrame({
            SCORE: score,
            DEVIATION: (score - grouped.transform("mean")) / grouped.transform("std"),
            GAP_TO_SECOND: score - RaceOrderStatistic(RaceOrder.LARGEST_FIRST).best_other(score, race),
            RANK: grouped.rank(ascending=False, method="min"),
        }, index=features.index).astype("float64")

    def _score(self, features: pd.DataFrame) -> pd.Series:
        index = pd.to_numeric(features[ABILITY_INDEX], errors="coerce")
        carried = pd.to_numeric(features[CARRIED], errors="coerce")
        return index - POINTS_PER_KG * (carried - BASE_CARRIED_KG)
