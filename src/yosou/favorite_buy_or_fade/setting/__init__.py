"""この予想の方針（設計書 14）。

| 名前 | 中身 |
|---|---|
| ``default_settings.toml`` | 方針の初期値。項目の意味はファイルのコメント |
| ``BuyOrFadeSettings`` | 方針の値。初期値に利用者の設定ファイルを重ねて作る |
| ``option_names.py`` | 名前で選ぶ項目（単位の分け方・数の列のそろえ方・カテゴリの直し方・列ごとの重み）に書ける値 |
"""

from .buy_or_fade_settings import DEFAULT_SETTINGS_PATH, BuyOrFadeSettings
from .option_names import (
    CATEGORICAL_ENCODINGS, COLUMN_WEIGHTINGS, ENCODING_ONE_HOT, ENCODING_OUT_RATE, SCALING_RANK, SCALING_STANDARD,
    SCALINGS, SPLIT_BY_COURSE, SPLIT_NONE, UNIT_SPLITS, WEIGHTING_AUC, WEIGHTING_NONE,
)

__all__ = [
    "BuyOrFadeSettings", "DEFAULT_SETTINGS_PATH",
    "SPLIT_BY_COURSE", "SPLIT_NONE", "UNIT_SPLITS",
    "SCALING_STANDARD", "SCALING_RANK", "SCALINGS",
    "ENCODING_ONE_HOT", "ENCODING_OUT_RATE", "CATEGORICAL_ENCODINGS",
    "WEIGHTING_NONE", "WEIGHTING_AUC", "COLUMN_WEIGHTINGS",
]
