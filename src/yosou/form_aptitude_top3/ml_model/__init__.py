"""機械学習のモデル。過去のレースで学習して、「3着以内に入る確率」を出す（データの形を表すデータモデルではない）。

| クラス | 仕事 |
|---|---|
| ``ProbabilityModel`` | 2つのモデルに共通の決まり（インターフェース） |
| ``LightGbmModel`` | LightGBM で学習・予測する（設計書 12） |
| ``LightGbmEncoder`` | 特徴量を、LightGBM が受け取れる形に変える |
| ``CatBoostModel`` | CatBoost で学習・予測する（設計書 13） |
| ``CatBoostEncoder`` | 特徴量を、CatBoost が受け取れる形に変える |
| ``EnsembleModel`` | 2つのモデルの予測確率を平均する |

``MEMBER_TYPES`` は、アンサンブルに入れるモデルのクラスの並び。学習済みモデルのファイルへの保存は ``repository/`` の ``ModelRepository``。
"""

from .catboost_encoder import CatBoostEncoder
from .catboost_model import CatBoostModel
from .ensemble_model import EnsembleModel
from .lightgbm_encoder import LightGbmEncoder
from .lightgbm_model import LightGbmModel
from .member_types import MEMBER_TYPES
from .probability_model import FeatureData, ProbabilityModel

__all__ = [
    "ProbabilityModel", "FeatureData", "LightGbmModel", "LightGbmEncoder",
    "CatBoostModel", "CatBoostEncoder", "EnsembleModel", "MEMBER_TYPES",
]
