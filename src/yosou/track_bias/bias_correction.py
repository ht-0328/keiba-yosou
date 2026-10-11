"""使う傾きと馬の位置から、馬ごとのバイアスの補正を出す。"""

from __future__ import annotations

import pandas as pd

from . import names
from .positions import Positions

#: 馬ごとの表の列（race_id・horse_id と、特徴量になる5列）。
COLUMNS: tuple[str, ...] = (
    names.RACE_ID, "horse_id", names.INNER_SLOPE_FEATURE, names.FRONT_SLOPE_FEATURE, names.INNER_PART, names.FRONT_PART, names.CORRECTION,
)


class BiasCorrection:
    """バイアスの補正 B = 使う内の傾き × 内らしさ + 使う前の傾き × 予想の前らしさ（設計書「買うレースと買い目を決める」06 の 1）。

    単位は3着以内の確率のポイント。内の分と前の分も別に出す（モデルがどちらが効くかを学べるように）。
    ``entries`` は 1行 = 1頭で、``race_id``・``horse_id``・``horse_no``・``field_size`` と展開の予想④（``corner4_pred``。0 が先頭、1 が最後）を持つ。
    ``used`` はレースごとの使う傾き（``race_id`` を index にした ``USED_INNER``・``USED_FRONT``）。
    ④ の無い馬は前の分が欠損値で、B も欠損値。例（架空）: 使う内の傾き +0.074 で、16頭立ての2番（内らしさ 0.433）なら内の分は +0.032。
    """

    def __init__(self) -> None:
        self._positions = Positions()

    def of(self, entries: pd.DataFrame, used: pd.DataFrame) -> pd.DataFrame:
        """列は ``COLUMNS``。行の並びと index は ``entries`` と同じ。"""
        race_ids = entries[names.RACE_ID].astype(str)
        inner_slope = race_ids.map(used[names.USED_INNER]).astype("float64")
        front_slope = race_ids.map(used[names.USED_FRONT]).astype("float64")
        inner_part = inner_slope * self._positions.innerness(entries["horse_no"], entries["field_size"])
        front_part = front_slope * self._positions.frontness_of_position(entries["corner4_pred"])
        return pd.DataFrame({
            names.RACE_ID: race_ids, "horse_id": entries["horse_id"].astype(str),
            names.INNER_SLOPE_FEATURE: inner_slope, names.FRONT_SLOPE_FEATURE: front_slope,
            names.INNER_PART: inner_part, names.FRONT_PART: front_part, names.CORRECTION: inner_part + front_part,
        }, index=entries.index)
