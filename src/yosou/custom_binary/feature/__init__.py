"""特徴量の決まり・登録・計算（設計書 09）。

| 名前 | 仕事 |
|---|---|
| ``FeatureDefinition`` | 特徴量1個の決まり（インターフェース） |
| ``FeatureRegistry`` | 登録された特徴量の一覧。誤りを検出し、依存の順に並べる |
| ``DefaultRegistry`` | 選べる特徴量の一覧（共通の特徴量 + ``registrations.py`` の ``ADDITIONAL_FEATURES``）を作る |
| ``SelectedFeatureBuilder`` | 選んだ特徴量と条件の列を、依存の順に1回ずつ計算する |
| ``GroupColumn``・``BuiltinFeatures`` | 共通のまとまり（A〜K）の1列を、1項目ずつ選べる特徴量にする |
| ``PoolProbability``・``PoolGap``・``PoolFeatureList`` | 券種オッズの特徴量 |
| ``registrations.py`` | 特徴量の登録場所。新しい特徴量は ``ADDITIONAL_FEATURES`` に1行足す |
"""

from .definition import FeatureDefinition
from .registry import FeatureRegistry

__all__ = ["FeatureDefinition", "FeatureRegistry"]
