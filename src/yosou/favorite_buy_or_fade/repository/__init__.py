"""ファイルと元DB の読み書き。ほかの予想と共通の SQL は ``yosou.shared.repository`` にあり、ここには
この予想だけが使うもの（学習したモデルの一式と、評価で使う締め切り前の1番人気）を置く。

| 名前 | 仕事 |
|---|---|
| ``SimilarityModelRepository`` | 学習した近さのモデルの一式と方針を、ファイルに書き込む・読み込む |
| ``PreDeadlineFavoriteRepository`` | 締め切り前の単勝オッズで1番人気だった馬を、元DB から読む（SQL 1つ） |
"""

from .pre_deadline_favorite_repository import PreDeadlineFavoriteRepository
from .similarity_model_repository import MODEL_FILE, SETTINGS_FILE, SimilarityModelRepository

__all__ = ["SimilarityModelRepository", "PreDeadlineFavoriteRepository", "MODEL_FILE", "SETTINGS_FILE"]
