"""選べる特徴量の一覧（登録）を作る。"""

from .builtin_features import BuiltinFeatures
from .registrations import ADDITIONAL_FEATURES
from .registry import FeatureRegistry


class DefaultRegistry:
    """共通の特徴量と、``registrations.py`` の ``ADDITIONAL_FEATURES``（券種オッズ・利用者が足したもの）を登録する。"""

    def build(self) -> FeatureRegistry:
        return FeatureRegistry((*BuiltinFeatures().all(), *ADDITIONAL_FEATURES))
