"""展開スコアを、予想の特徴量にするときの一覧。"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind

from . import names

#: 特徴量の名前（展開スコアと、脚質ごとの内訳の 5個）。
DEVELOPMENT_SCORE_NAMES: tuple[str, ...] = (names.SCORE, *names.CONTRIBUTIONS)
#: S. 展開スコア（5個。どれも数値）。展開の予想の結果（P）と同じく、その時点の展開のモデルの予測から作るので木曜から分かる。
#: 研究「既存モデルの改善」が、全頭の3着以内の予想に足して時点ごとに7つの区切りで比べる（設計書「買うレースと買い目を決める」07 の 1）。
DEVELOPMENT_SCORE_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "S", FeatureKind.NUMERIC) for name in DEVELOPMENT_SCORE_NAMES)
