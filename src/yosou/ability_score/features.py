"""能力スコアを、予想の特徴量にするときの一覧。"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind

#: 列の名前。能力スコア（能力指数を今回の斤量で直したもの）と、レース内の位置の3つ。
SCORE = "能力スコア"
DEVIATION = "能力スコア_偏差"
GAP_TO_SECOND = "能力スコア_2位との差"
RANK = "能力スコア_順位"
#: 特徴量の名前（4個）。
ABILITY_SCORE_NAMES: tuple[str, ...] = (SCORE, DEVIATION, GAP_TO_SECOND, RANK)
#: T. 能力スコア（4個。どれも数値）。馬の力の材料（M）の能力指数と今回の斤量から作るので、M と同じく木曜から分かる。
#: 研究「既存モデルの改善」の入口⑭が、全頭の予想に足して時点ごと・目的変数ごとに7つの区切りで比べる（設計書「買うレースと買い目を決める」04）。
ABILITY_SCORE_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "T", FeatureKind.NUMERIC) for name in ABILITY_SCORE_NAMES)
