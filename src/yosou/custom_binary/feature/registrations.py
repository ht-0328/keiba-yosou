"""特徴量の登録場所。新しいクラスをimportし、ADDITIONAL_FEATURESに1行追加する。"""

from .builtin import builtin_features
from .definition import FeatureDefinition
from .pool_features import pool_features
from .registry import FeatureRegistry


ADDITIONAL_FEATURES: tuple[FeatureDefinition, ...] = (
    *pool_features(),
    # NewFeature(),
)


def default_registry() -> FeatureRegistry:
    return FeatureRegistry((*builtin_features(), *ADDITIONAL_FEATURES))
