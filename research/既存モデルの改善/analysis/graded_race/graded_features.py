"""まとまり W（重賞の格と実績。14個）の特徴量の一覧（重賞の予想の設計書 09 の W）。"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind

_N, _C = FeatureKind.NUMERIC, FeatureKind.CATEGORICAL

#: 重賞かどうかの列の名前。行の重みもこの列で決める。
IS_GRADED = "重賞か"
#: 格の名前の並び（設計書 06 の図3）。前走の格には「障害」「前走なし」も入る。
GRADE_STEPS: tuple[str, ...] = ("条件", "OP", "L", "G3", "G2", "G1")

#: W の14個。どれも木曜から分かる（出走馬名表のレースの格・斤量と、それより前の開催日の確定成績から作る）。
W_FEATURES: tuple[Feature, ...] = (
    Feature(IS_GRADED, "W", _N),
    Feature("格", "W", _C),
    Feature("重量種別", "W", _C),
    Feature("トップハンデとの差", "W", _N),
    Feature("前走の格", "W", _C),
    Feature("重賞の出走数", "W", _N),
    Feature("重賞の3着以内の数", "W", _N),
    Feature("重賞の勝利数", "W", _N),
    Feature("G1の3着以内の数", "W", _N),
    Feature("今回の格以上での3着以内の数", "W", _N),
    Feature("直近の重賞の着順", "W", _N),
    Feature("同じ重賞の出走数", "W", _N),
    Feature("同じ重賞の3着以内の数", "W", _N),
    Feature("前年の同じ重賞の着順", "W", _N),
)
W_NAMES: tuple[str, ...] = tuple(feature.name for feature in W_FEATURES)
#: カテゴリの W（表に足すときに文字列にそろえる）。
W_CATEGORICAL: tuple[str, ...] = tuple(feature.name for feature in W_FEATURES if feature.is_categorical)
