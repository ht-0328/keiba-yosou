"""馬体重の表の割引を、予想の特徴量にするときの一覧。"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind, PredictionTiming

from . import names

#: 特徴量の名前（1個）。
WEIGHT_DISCOUNT_NAMES: tuple[str, ...] = (names.DISCOUNT,)
#: V. 馬体重の表の割引（1個。数値）。馬体重の発表は当日なので当日から分かる。研究「既存モデルの改善」の入口⑭が、全頭の予想に足して
#: 目的変数ごとに7つの区切りで比べる（設計書「買うレースと買い目を決める」06 の 2）。
WEIGHT_DISCOUNT_FEATURES: tuple[Feature, ...] = tuple(
    Feature(name, "V", FeatureKind.NUMERIC, PredictionTiming.RACE_DAY) for name in WEIGHT_DISCOUNT_NAMES)
