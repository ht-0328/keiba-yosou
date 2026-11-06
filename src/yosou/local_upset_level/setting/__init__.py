"""この予想のハイパーパラメータの初期値（設計書 14）。

設定ファイルを読むクラス（``HyperparameterSettings`` など）は ``yosou.shared.setting``。
初期値は予想ごとに決めるので、ファイル（``default_settings.toml``）はここに置き、そのパスを
``HyperparameterSettings.load(path, defaults=DEFAULT_SETTINGS_PATH)`` に渡す。中身は中央の荒れ具合の初期値と同じ値から始める。
4券種 × 3つの時点のモデルは、同じ設定で学習する。
"""

from pathlib import Path

#: この予想の初期値の設定ファイル。
DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "default_settings.toml"

__all__ = ["DEFAULT_SETTINGS_PATH"]
