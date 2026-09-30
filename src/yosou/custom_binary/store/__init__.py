"""学習したモデルのファイルの読み書き（設計書 12 の「6. 保存」）。

| 名前 | 読む・書くもの |
|---|---|
| ``ModelStore`` | 学習した2つのモデルと、設定・特徴量の形・コードの版・検証とテストの成績を、1つのフォルダに読み書きする |
| ``CodeVersion`` | 学習したときのコードの版（Git のコミットと、Pythonソースのハッシュ） |
| ``model_location.py`` | 学習したモデルの置き場所（``MODELS_ROOT`` = ``reports/特徴量と条件を選んで予想/``） |

保存物にはクラスの置き場所を埋め込まない（設定は JSON、モデルは共通の ``ModelRepository`` が書く）ので、
クラスの置き場所を変えても、前に保存したモデルを読める。元DB を読む SQL は ``repository/``。
"""

from .code_version import CodeVersion
from .model_location import MODELS_ROOT, PROJECT_ROOT, YOSOU_NAME
from .model_store import ModelStore

__all__ = ["CodeVersion", "MODELS_ROOT", "ModelStore", "PROJECT_ROOT", "YOSOU_NAME"]
