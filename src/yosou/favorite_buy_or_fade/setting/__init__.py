"""この予想の方針（設計書 14）。

| 名前 | 中身 |
|---|---|
| ``default_settings.toml`` | 方針の初期値。項目の意味はファイルのコメント |
| ``BuyOrFadeSettings`` | 方針の値。初期値に利用者の設定ファイルを重ねて作る |
"""

from .buy_or_fade_settings import DEFAULT_SETTINGS_PATH, BuyOrFadeSettings

__all__ = ["BuyOrFadeSettings", "DEFAULT_SETTINGS_PATH"]
