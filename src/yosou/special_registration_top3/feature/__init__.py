"""この予想の特徴量の一覧と、この予想だけのまとまり（設計書 09）。

| 名前 | 仕事 |
|---|---|
| ``REGISTRATION_ABILITY_FEATURES`` | M の 202個から特別登録の時点に無い 34個（``UNAVAILABLE_NAMES``。騎手の 20個は ``JOCKEY_NAMES``）を除いた 168個 |
| ``SPECIAL_RACE_FEATURES``・``SpecialRaceFeatures`` | Y. 特別競走の印（1個）と、それを作るまとまり |
| ``BASE_CATALOG`` | ``FeatureBuilder`` が作る一覧（M 168・O 7・Y 1 の 176個） |
| ``CATALOG`` | この予想の一覧（T の4個を足した 180個） |
| ``FIELD_COMPARISON_NAMES`` | 同じレースの相手と比べる材料の 70個の名前（``backtest --variant 相手と比べない`` が外す） |
"""

from .feature_catalog import (
    BASE_CATALOG,
    CATALOG,
    FIELD_COMPARISON_NAMES,
    JOCKEY_NAMES,
    REGISTRATION_ABILITY_FEATURES,
    REGISTRATION_ABILITY_NAMES,
    SPECIAL_RACE,
    SPECIAL_RACE_FEATURES,
    UNAVAILABLE_NAMES,
)
from .special_race_features import SpecialRaceFeatures

__all__ = [
    "BASE_CATALOG", "CATALOG", "FIELD_COMPARISON_NAMES", "JOCKEY_NAMES", "REGISTRATION_ABILITY_FEATURES",
    "REGISTRATION_ABILITY_NAMES", "SPECIAL_RACE", "SPECIAL_RACE_FEATURES", "UNAVAILABLE_NAMES", "SpecialRaceFeatures",
]
