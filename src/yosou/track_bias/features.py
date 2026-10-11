"""トラックバイアスの補正を、予想の特徴量にするときの一覧。"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind, PredictionTiming

from . import names

#: 特徴量の名前（5個）。使う内の傾き・使う前の傾き（レースの値）と、馬ごとの内の分・前の分・その和（バイアスの補正 B）。
TRACK_BIAS_NAMES: tuple[str, ...] = (
    names.INNER_SLOPE_FEATURE, names.FRONT_SLOPE_FEATURE, names.INNER_PART, names.FRONT_PART, names.CORRECTION,
)
#: U. トラックバイアスの補正（5個。どれも数値）。馬番が決まる前日から分かる（前日は前の日の同じ馬場のレースだけ、当日はその日の
#: 先に終わったレースも数える）。研究「既存モデルの改善」の入口⑭が、全頭の予想に足して時点ごと・目的変数ごとに7つの区切りで比べる
#: （設計書「買うレースと買い目を決める」06 の 1）。
TRACK_BIAS_FEATURES: tuple[Feature, ...] = tuple(
    Feature(name, "U", FeatureKind.NUMERIC, PredictionTiming.DAY_BEFORE) for name in TRACK_BIAS_NAMES)
