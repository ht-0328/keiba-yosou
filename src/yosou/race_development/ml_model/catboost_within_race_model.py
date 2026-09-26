"""CatBoost の二値のモデルを、レースの中でそろえる。"""

from __future__ import annotations

from yosou.shared.ml_model import CatBoostModel

from .within_race_model import WithinRaceModel


class CatBoostWithinRaceModel(WithinRaceModel):
    """中のモデルを共通の ``CatBoostModel`` にした ``WithinRaceModel``（設計書 13）。"""

    name = "CatBoost"
    file_name = "catboost.cbm"
    inner_type = CatBoostModel
