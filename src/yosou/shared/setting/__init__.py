"""ハイパーパラメータの設定ファイル（TOML）を読む（設計書 14）。

| クラス | 仕事 |
|---|---|
| ``HyperparameterSettings`` | 2つのモデルの設定。設定ファイルを読む入口 |
| ``LightGbmSettings``・``CatBoostSettings`` | モデルごとの設定の値 |
| ``SettingsFile`` | TOML のファイルを辞書として読む |
| ``SettingsNameCheck`` | 書かれた名前が、初期値のファイルにあるかを確かめる |
| ``SettingsOverlay`` | 初期値に、利用者が書いた項目を重ねる |

初期値のファイル（``default_settings.toml``）は予想ごとに持ち、そのパスを ``HyperparameterSettings.load``
に渡す（手本の予想では ``yosou.form_aptitude_top3.setting.DEFAULT_SETTINGS_PATH``）。
"""

from .catboost_settings import CatBoostSettings
from .hyperparameter_settings import HyperparameterSettings
from .lightgbm_settings import LightGbmSettings

__all__ = ["HyperparameterSettings", "LightGbmSettings", "CatBoostSettings"]
