"""近さのモデル（設計書 12・13）。1番人気が、勝利・馬券内・馬券外のどのグループの馬に近いかを点数で出す。

| 名前 | 仕事 |
|---|---|
| ``MatrixOptions`` | 行列の作り方の方針（除く特徴量・まとまりの重み・欠損値の列・そろえ方・カテゴリの直し方・列ごとの重み） |
| ``FeatureMatrix`` | 特徴量の表を、距離を測れる数の行列にする（欠損値の埋め・そろえ方・カテゴリの直し方・重み） |
| ``StandardScaling``・``RankScaling`` | 数の列のそろえ方（標準化 か 順位） |
| ``OneHotEncoding``・``OutRateEncoding`` | カテゴリの列の直し方（one-hot か 馬券外率） |
| ``EqualWeighting``・``AucWeighting`` | 列ごとの重みの決め方（なし か 馬券外との AUC） |
| ``GroupSimilarity`` | 1つのグループの馬だけを覚え、そのグループへの近さの点数（0〜100）を出す。k近傍法 |
| ``UnitSimilarity`` | 1つの単位（芝ダート × 距離）の、3つのグループのモデルと共通の変換 |
| ``SimilarityModelSet`` | 学習したモデルの一式（単位の決め方・単位ごとのモデル・方針） |

点数の列の名前は ``score_columns.py``。
"""

from .auc_weighting import AucWeighting
from .equal_weighting import EqualWeighting
from .feature_matrix import FeatureMatrix
from .group_similarity import MIN_GROUP_ROWS, GroupSimilarity
from .matrix_options import MatrixOptions
from .one_hot_encoding import OneHotEncoding
from .out_rate_encoding import OutRateEncoding
from .rank_scaling import RankScaling
from .score_columns import SCORE_COLUMNS, UNIT
from .similarity_model_set import SimilarityModelSet
from .standard_scaling import StandardScaling
from .unit_similarity import UnitSimilarity

__all__ = [
    "MatrixOptions", "FeatureMatrix", "StandardScaling", "RankScaling", "OneHotEncoding", "OutRateEncoding",
    "EqualWeighting", "AucWeighting", "GroupSimilarity", "UnitSimilarity", "SimilarityModelSet",
    "SCORE_COLUMNS", "UNIT", "MIN_GROUP_ROWS",
]
