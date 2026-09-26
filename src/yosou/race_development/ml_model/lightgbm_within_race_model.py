"""LightGBM の二値のモデルを、レースの中でそろえる。"""

from __future__ import annotations

from yosou.shared.ml_model import LightGbmModel

from .within_race_model import WithinRaceModel


class LightGbmWithinRaceModel(WithinRaceModel):
    """中のモデルを共通の ``LightGbmModel`` にした ``WithinRaceModel``（設計書 12）。"""

    name = "LightGBM"
    file_name = "lightgbm.joblib"
    inner_type = LightGbmModel
