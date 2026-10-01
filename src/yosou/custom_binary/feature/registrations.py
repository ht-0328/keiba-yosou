"""特徴量の登録場所。新しいクラスをimportし、ADDITIONAL_FEATURESに1行追加する。

登録した一覧は ``DefaultRegistry``（``default_registry.py``）が、共通の特徴量と合わせて使う。
"""

from .definition import FeatureDefinition
from .pool_feature_list import PoolFeatureList


ADDITIONAL_FEATURES: tuple[FeatureDefinition, ...] = (
    *PoolFeatureList().all(),
    # NewFeature(),
)
