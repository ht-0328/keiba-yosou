"""多クラス分類のアンサンブルに入れるモデルのクラス。"""

from __future__ import annotations

from .catboost_multiclass_model import CatBoostMulticlassModel
from .class_probability_model import ClassProbabilityModel
from .lightgbm_multiclass_model import LightGbmMulticlassModel

#: 多クラス分類の予想（荒れ具合）は、時点ごとにこの並びのモデルを1つずつ学習して保存し、クラスごとの確率を平均する。
CLASS_MEMBER_TYPES: tuple[type[ClassProbabilityModel], ...] = (LightGbmMulticlassModel, CatBoostMulticlassModel)
