"""ファイルの読み書き。元DB を読む SQL は、共通の ``yosou.shared.repository`` にある。

| 名前 | 仕事 |
|---|---|
| ``SimilarityModelRepository`` | 学習した近さのモデルの一式と方針を、ファイルに書き込む・読み込む |
"""

from .similarity_model_repository import MODEL_FILE, SETTINGS_FILE, SimilarityModelRepository

__all__ = ["SimilarityModelRepository", "MODEL_FILE", "SETTINGS_FILE"]
