"""1着・2着・3着を分けたモデル: 票の表（``PoolTables``）で条件つきロジットを当てはめ、3連単の全部の組に P(a) P(b|a) P(c|a,b) と期待値を付ける。"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .conditional_logit import ConditionalLogit
from .pool_tables import PoolTables
from .pool_tables_builder import group_key
from .position_coefficients import PositionCoefficients
from .position_features import FIRST_FEATURES, HORSE_CARRY, SECOND_FEATURES, THIRD_FEATURES, PositionFeatures

#: 組の表に付ける列。
P1, P2, P3, PROBABILITY, EV = "P1", "P2", "P3", "P", "ev"
_FIRST, _SECOND, _THIRD = 1.0, 2.0, 3.0


@dataclass(frozen=True)
class PositionModel:
    """``fit`` は複数の期間の表で係数を求め、``predict`` は1つの期間の組の表に確率と期待値を付ける。

    - 1着: レースの全頭の softmax。
    - 2着: 実際の1着 a* を除いた馬の softmax（学ぶとき）。予測は全部の a について、a を除いた馬の softmax。
    - 3着: 実際の 1着 a*・2着 b* を除いた馬の softmax（学ぶとき）。予測は全部の (a, b) について。
    同着のレース（1〜3着が1頭ずつでない）は学ぶときに外す。
    """

    first_features: tuple[str, ...] = FIRST_FEATURES
    second_features: tuple[str, ...] = SECOND_FEATURES
    third_features: tuple[str, ...] = THIRD_FEATURES
    logit: ConditionalLogit = field(default_factory=ConditionalLogit)

    @property
    def feature_names(self) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        return self.first_features, self.second_features, self.third_features

    def fit(self, periods: list[PoolTables]) -> PositionCoefficients:
        rows: tuple[list[pd.DataFrame], list[pd.DataFrame], list[pd.DataFrame]] = ([], [], [])
        for tables in periods:
            first, second, third = self._training_rows(tables)
            rows[0].append(first)
            rows[1].append(second)
            rows[2].append(third)
        betas = []
        for parts, features in zip(rows, self.feature_names, strict=True):
            table = pd.concat(parts)
            chosen = table.groupby("g")["y"].transform("sum").eq(1.0)   # 選ばれた行の無いグループ（オッズの無い組など）は外す
            table = table[chosen]
            betas.append(self.logit.fit(table[list(features)].to_numpy(dtype=np.float64), table["g"].to_numpy(), table["y"].to_numpy(dtype=np.float64)))
        return PositionCoefficients.of(self.feature_names, tuple(betas))

    def predict(self, tables: PoolTables, coefficients: PositionCoefficients) -> pd.DataFrame:
        """``combos`` の列に ``P1``・``P2``・``P3``・``P``・``ev`` を足した表（``odds``・``payout`` も残す）。"""
        features = PositionFeatures()
        horses = features.horses(tables.horses)
        horses[P1] = self.logit.probabilities(horses[list(self.first_features)].to_numpy(dtype=np.float64) @ coefficients.vector(0), horses["race_id"].to_numpy())
        carry = horses[["race_id", "horse_no", *HORSE_CARRY]]
        pairs = features.pairs(tables.pairs).merge(carry.rename(columns={"horse_no": "second"}), on=["race_id", "second"], how="inner")
        key_a = group_key(pairs["race_id"].to_numpy(), pairs["first"].to_numpy())
        pairs[P2] = self.logit.probabilities(pairs[list(self.second_features)].to_numpy(dtype=np.float64) @ coefficients.vector(1), key_a)
        combos = features.combos(tables.combos).merge(carry.rename(columns={"horse_no": "third"}), on=["race_id", "third"], how="inner")
        combos[P3] = self.logit.probabilities(combos[list(self.third_features)].to_numpy(dtype=np.float64) @ coefficients.vector(2), combos["key_ab"].to_numpy())
        combos = combos[["race_id", "first", "second", "third", "odds", "payout", "m", P3]]
        combos = combos.merge(pairs[["race_id", "first", "second", P2]], on=["race_id", "first", "second"], how="inner")
        combos = combos.merge(horses[["race_id", "horse_no", P1]].rename(columns={"horse_no": "first"}), on=["race_id", "first"], how="inner")
        combos[PROBABILITY] = combos[P1] * combos[P2] * combos[P3]
        combos[EV] = combos[PROBABILITY] * combos["odds"].astype(np.float64)
        return combos.reset_index(drop=True)

    def _training_rows(self, tables: PoolTables) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        features = PositionFeatures()
        h = features.horses(tables.horses)
        finish = h["finish"]
        counts = h.assign(f1=finish.eq(_FIRST), f2=finish.eq(_SECOND), f3=finish.eq(_THIRD)).groupby("race_id")[["f1", "f2", "f3"]].sum()
        clean = counts[(counts["f1"] == 1) & (counts["f2"] == 1) & (counts["f3"] == 1)].index
        h = h[h["race_id"].isin(clean)]
        first = h.assign(y=h["finish"].eq(_FIRST).astype(float), g=h["race_id"])[[*self.first_features, "y", "g"]]
        winners = h[h["finish"] == _FIRST][["race_id", "horse_no"]].rename(columns={"horse_no": "first"})
        rest = h[h["finish"] != _FIRST].merge(winners, on="race_id")
        rest = rest.merge(features.pairs(tables.pairs), left_on=["race_id", "first", "horse_no"], right_on=["race_id", "first", "second"], how="inner")
        second = rest.assign(y=rest["finish"].eq(_SECOND).astype(float), g=rest["race_id"])[[*self.second_features, "y", "g"]]
        seconds = h[h["finish"] == _SECOND][["race_id", "horse_no"]].rename(columns={"horse_no": "second"})
        rest3 = h[~h["finish"].isin([_FIRST, _SECOND])].merge(winners, on="race_id").merge(seconds, on="race_id")
        combos = features.combos(tables.combos[["race_id", "first", "second", "third", "m3", "m3t"]])
        rest3 = rest3.merge(combos, left_on=["race_id", "first", "second", "horse_no"], right_on=["race_id", "first", "second", "third"], how="inner")
        third = rest3.assign(y=rest3["finish"].eq(_THIRD).astype(float), g=rest3["race_id"])[[*self.third_features, "y", "g"]]
        return first, second, third
