"""前走の不利を、予想の特徴量にするときの一覧。"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind

from . import names

#: 列の名前。前走の不利の程度（0 なし〜3 大）を種類ごとに、前走を見直すか（0/1）、前走と前々走の程度の最大。
PREVIOUS_LATE_START = "前走の不利_出遅れ"
PREVIOUS_PACE = "前走の不利_展開"
PREVIOUS_BIAS = "前走の不利_バイアス"
PREVIOUS_REVIEW = "前走の見直す"
PREVIOUS_MAX = "近2走の不利の最大"
#: 特徴量の名前（5個）。
PREVIOUS_HANDICAP_NAMES: tuple[str, ...] = (PREVIOUS_LATE_START, PREVIOUS_PACE, PREVIOUS_BIAS, PREVIOUS_REVIEW, PREVIOUS_MAX)
#: X. 前走の不利（5個。どれも数値）。前走の結果から決まるので木曜から分かる。研究「既存モデルの改善」の入口⑭が、全頭の予想に足して
#: 時点ごと・目的変数ごとに7つの区切りで比べる（設計書「買うレースと買い目を決める」08 の 3「次走への活かし方」）。
PREVIOUS_HANDICAP_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "X", FeatureKind.NUMERIC) for name in PREVIOUS_HANDICAP_NAMES)
