"""機械学習のモデル。過去のレースで学習して、目的変数が 1 になる確率（か、クラスごとの確率）を出す
（データの形を表すデータモデルではない）。

何が 1 か、クラスが何かは予想ごとに決まる（手本の予想では「3着以内に入る確率」、荒れ具合の予想では
「固い・中荒れ・大荒れ・超荒れ」の確率）。ここのクラスは、学習データの ``label`` をそのまま当てさせるだけで、
目的変数の意味を知らない。

| クラス | 仕事 |
|---|---|
| ``ProbabilityModel`` | 二値分類の2つのモデルに共通の決まり（インターフェース） |
| ``ClassProbabilityModel`` | 多クラス分類の2つのモデルに共通の決まり（インターフェース。``predict_proba`` が行数 × クラスの数） |
| ``LightGbmModel`` | LightGBM で学習・予測する（設計書 12） |
| ``LightGbmMulticlassModel`` | LightGBM で多クラス分類の学習・予測をする（荒れ具合の設計書 12） |
| ``LightGbmEncoder`` | 特徴量を、LightGBM が受け取れる形に変える |
| ``CatBoostModel`` | CatBoost で学習・予測する（設計書 13） |
| ``CatBoostMulticlassModel`` | CatBoost で多クラス分類の学習・予測をする（荒れ具合の設計書 13） |
| ``CatBoostEncoder`` | 特徴量を、CatBoost が受け取れる形に変える |
| ``EnsembleModel`` | 2つのモデルの予測確率を平均する（1列でも、クラスごとの列でも） |
| ``BaselineCheck`` | モデルが目的変数の基準（オッズから作ったロジット）を出発点にして学んだかと、予測に渡す基準の取り出し |

``MEMBER_TYPES``・``CLASS_MEMBER_TYPES`` は、アンサンブルに入れるモデルのクラスの並び（二値分類・多クラス分類）。
学習済みモデルのファイルへの保存は ``repository/`` の ``ModelRepository``。
"""

from .catboost_encoder import CatBoostEncoder
from .catboost_model import CatBoostModel
from .catboost_multiclass_model import CatBoostMulticlassModel
from .class_member_types import CLASS_MEMBER_TYPES
from .class_probability_model import ClassProbabilityModel
from .ensemble_model import EnsembleModel, Member
from .lightgbm_encoder import LightGbmEncoder
from .lightgbm_model import LightGbmModel
from .lightgbm_multiclass_model import LightGbmMulticlassModel
from .member_types import MEMBER_TYPES
from .probability_model import FeatureData, ProbabilityModel

__all__ = [
    "ProbabilityModel", "ClassProbabilityModel", "Member", "FeatureData",
    "LightGbmModel", "LightGbmMulticlassModel", "LightGbmEncoder",
    "CatBoostModel", "CatBoostMulticlassModel", "CatBoostEncoder",
    "EnsembleModel", "MEMBER_TYPES", "CLASS_MEMBER_TYPES",
]
