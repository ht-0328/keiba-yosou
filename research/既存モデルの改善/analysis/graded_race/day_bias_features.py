"""まとまり D（その日の馬場の傾向）の特徴量の一覧。研究「重賞の事例から材料を作る」の段2。

どれも、同じ開催日・同じ競馬場・同じ芝ダで、そのレースの2つ前のレースまでに終わったレースの3着以内の馬から作る
（通過順の速報は発走の 10〜30 分後に届くので、発走10分前に分かるのは2つ前のレースまで）。
"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind

_N = FeatureKind.NUMERIC

#: D の5つ。
D_FEATURES: tuple[Feature, ...] = (
    Feature("その日の先のレースの数", "D", _N),
    Feature("その日の前残りの度合い", "D", _N),
    Feature("その日の内の度合い", "D", _N),
    Feature("脚質と馬場の合い具合", "D", _N),
    Feature("枠と馬場の合い具合", "D", _N),
)
D_NAMES: tuple[str, ...] = tuple(feature.name for feature in D_FEATURES)
