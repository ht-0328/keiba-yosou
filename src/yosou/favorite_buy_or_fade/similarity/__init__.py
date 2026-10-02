"""近さのモデル（設計書 12・13）。1番人気が、勝利・馬券内・馬券外のどのグループの馬に近いかを点数で出す。

| 名前 | 仕事 |
|---|---|
| ``FeatureMatrix`` | 特徴量の表を、距離を測れる数の行列にする（欠損値の埋め・標準化・one-hot・重み） |
| ``GroupSimilarity`` | 1つのグループの馬だけを覚え、そのグループへの近さの点数（0〜100）を出す。k近傍法 |
| ``UnitSimilarity`` | 1つの単位（芝ダート × 距離）の、3つのグループのモデルと共通の変換 |
| ``SimilarityModelSet`` | 学習したモデルの一式（単位の決め方・単位ごとのモデル・方針） |

点数の列の名前は ``score_columns.py``。
"""

from .feature_matrix import FeatureMatrix
from .group_similarity import MIN_GROUP_ROWS, GroupSimilarity
from .score_columns import SCORE_COLUMNS, UNIT
from .similarity_model_set import SimilarityModelSet
from .unit_similarity import UnitSimilarity

__all__ = [
    "FeatureMatrix", "GroupSimilarity", "UnitSimilarity", "SimilarityModelSet",
    "SCORE_COLUMNS", "UNIT", "MIN_GROUP_ROWS",
]
