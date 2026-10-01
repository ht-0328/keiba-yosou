"""共通のまとまり（A〜K）の特徴量を、1項目ずつ選べる形で並べる。"""

from yosou.shared.feature.feature_catalog import BASE_FEATURES, ODDS_FEATURES, POPULARITY_FEATURES

from .group_column import COMPARISON_DEPENDENCIES, GroupColumn


class BuiltinFeatures:
    """共通の特徴量の一覧（基本・人気の履歴・オッズ）の1項目ずつを ``GroupColumn`` にする。"""

    def all(self) -> tuple[GroupColumn, ...]:
        return tuple(GroupColumn(
            feature.name, feature.name, feature.kind, feature.known_from,
            COMPARISON_DEPENDENCIES if feature.group == "G" else (), feature.group,
        ) for feature in (*BASE_FEATURES, *POPULARITY_FEATURES, *ODDS_FEATURES))
