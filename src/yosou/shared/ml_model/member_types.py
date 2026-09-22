"""アンサンブルに入れるモデルのクラス。"""

from __future__ import annotations

from .catboost_model import CatBoostModel
from .lightgbm_model import LightGbmModel
from .probability_model import ProbabilityModel

#: 時点ごとに、この並びのモデルを1つずつ学習して保存し、予測確率を平均する。
MEMBER_TYPES: tuple[type[ProbabilityModel], ...] = (LightGbmModel, CatBoostModel)
