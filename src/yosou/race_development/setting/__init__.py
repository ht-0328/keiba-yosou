"""この予想のハイパーパラメータの初期値（設計書 14）。

設定ファイルを読むクラス（``HyperparameterSettings`` など）は ``yosou.shared.setting``。

| ファイル | 中身 |
|---|---|
| ``default_settings.toml`` | 初期値（手本と同じ値）。学習（train）が使う |
| ``backtest_settings.toml`` | 年ごとの確かめ（backtest）の既定の置き換え。学習率を上げ、木の数の上限を下げて速くする |
"""

from pathlib import Path

#: この予想の初期値の設定ファイル。
DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "default_settings.toml"
#: 年ごとの確かめの既定の置き換えのファイル（``--config`` を省略したときに使う）。
BACKTEST_SETTINGS_PATH = Path(__file__).resolve().parent / "backtest_settings.toml"

__all__ = ["DEFAULT_SETTINGS_PATH", "BACKTEST_SETTINGS_PATH"]
