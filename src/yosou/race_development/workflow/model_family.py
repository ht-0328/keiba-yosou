"""モデルの種類（何を返すモデルか）。"""

from __future__ import annotations

from enum import Enum


class ModelFamily(Enum):
    """予想のモデルの種類（設計書 04 の 1）。種類ごとに、LightGBM と CatBoost のクラスと、予測の返し方が決まる。

    - ``WITHIN_RACE``: 二値分類の確率を、レースの中で合計 1 にそろえる（① 先頭・⑦ 1着）。
    - ``MULTICLASS``: 3クラスの確率（② 序盤の位置・③ ペースの区分）。
    - ``QUANTILE``: 10%・50%・90% の分位点（③ 前半タイム・⑥ 後半タイム）。
    - ``REGRESSION``: 値そのもの（④ 4コーナーの位置・⑤ 上がりの速さ）。
    """

    WITHIN_RACE = "within_race"
    MULTICLASS = "multiclass"
    QUANTILE = "quantile"
    REGRESSION = "regression"
