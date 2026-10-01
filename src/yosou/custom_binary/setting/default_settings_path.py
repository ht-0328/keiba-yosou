"""この予想のハイパーパラメータの初期値の設定ファイル（設計書 14）。"""

from pathlib import Path

#: この予想の初期値の設定ファイル。値は手本の予想と同じだが、予想のパッケージどうしで import しないよう、ここに持つ。
DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "default_settings.toml"
