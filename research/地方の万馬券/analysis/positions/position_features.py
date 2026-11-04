"""1着・2着・3着の条件つきロジットの特徴量（対数）: 全頭の予想①のモデルごとの確率と、単勝・3連単・馬単・3連複・複勝の票の見立て。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_FLOOR = 1e-9
#: 1着（レース内の softmax）。LightGBM と CatBoost の 1着の確率を分けて使う（2モデルの食い違いが効く）。
FIRST_FEATURES: tuple[str, ...] = ("log_p1_lgb", "log_p1_cat", "log_s", "log_m_a", "log_m_ax", "log_m1t", "log_px")
#: 2着（1着 a を除いた馬の softmax）。``log_m2``・``log_m2x``・``log_m2t`` は a との対の票。
SECOND_FEATURES: tuple[str, ...] = ("log_p1", "log_p3_lgb", "log_p3_cat", "log_s", "log_m2", "log_m2x", "log_m2t", "log_px")
#: 3着（1着 a・2着 b を除いた馬の softmax）。``log_m3``・``log_m3t`` は a・b との組の票。
THIRD_FEATURES: tuple[str, ...] = ("log_p1", "log_p3_lgb", "log_p3_cat", "log_s", "log_m3", "log_m3t", "log_px")
#: 3連単の票だけを使う（馬単・3連複・複勝の票を足さない）ときの特徴量。
FIRST_FEATURES_TRIFECTA_ONLY: tuple[str, ...] = ("log_p1_lgb", "log_p1_cat", "log_s", "log_m_a")
SECOND_FEATURES_TRIFECTA_ONLY: tuple[str, ...] = ("log_p1", "log_p3_lgb", "log_p3_cat", "log_s", "log_m2")
THIRD_FEATURES_TRIFECTA_ONLY: tuple[str, ...] = ("log_p1", "log_p3_lgb", "log_p3_cat", "log_s", "log_m3")

_HORSE_SOURCES: tuple[str, ...] = ("p1", "p1_lgb", "p1_cat", "p3", "p3_lgb", "p3_cat", "s", "m_a", "m_ax", "m1t", "px")
_PAIR_SOURCES: tuple[str, ...] = ("m2", "m2x", "m2t")
_COMBO_SOURCES: tuple[str, ...] = ("m3", "m3t")
#: 馬の表から対・組の表に付け替える列（2着・3着の候補 b・c の特徴量）。
HORSE_CARRY: tuple[str, ...] = ("log_p1", "log_p3", "log_p3_lgb", "log_p3_cat", "log_s", "log_px")


@dataclass(frozen=True)
class PositionFeatures:
    """``horses``・``pairs``・``combos`` に、元の列の対数（``log_`` を付けた名前）を足して返す。"""

    def horses(self, table: pd.DataFrame) -> pd.DataFrame:
        return self._with_logs(table, _HORSE_SOURCES)

    def pairs(self, table: pd.DataFrame) -> pd.DataFrame:
        return self._with_logs(table, _PAIR_SOURCES)

    def combos(self, table: pd.DataFrame) -> pd.DataFrame:
        return self._with_logs(table, _COMBO_SOURCES)

    def _with_logs(self, table: pd.DataFrame, sources: tuple[str, ...]) -> pd.DataFrame:
        logs = {f"log_{name}": np.log(pd.to_numeric(table[name], errors="coerce").astype(float).clip(lower=_FLOOR)) for name in sources if name in table.columns}
        return table.assign(**logs)
