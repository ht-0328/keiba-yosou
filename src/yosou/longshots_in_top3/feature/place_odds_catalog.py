"""M. 複勝オッズから見た評価（4個）の一覧（設計書 09 の M）。"""

from __future__ import annotations

from yosou.shared.feature import Feature, FeatureKind, PredictionTiming

#: 特徴量の名前（学習データの列名）。評価用の列「複勝オッズ（最低）」「複勝オッズ（最高）」と混ざらないよう、別の名前にする。
PLACE_ODDS_LOW_FEATURE = "複勝の最低オッズ"
PLACE_ODDS_HIGH_FEATURE = "複勝の最高オッズ"
PLACE_MARKET_RATE = "複勝オッズから見た3着以内率"
PLACE_TO_WIN_RATIO = "複勝と単勝の3着以内率の比"

#: 穴馬の予想だけが A〜L に足す、M. 複勝オッズから見た評価（4個）。複勝オッズは単勝オッズと同じ o1 に入るので、
#: 単勝オッズと同じく前日から分かる。作るのは ``place_odds_features.py``。
#: 期待値の高い馬に残る偏り（設計書 15 の 15）を、モデルの側で直すために足した（設計書 15 の 16）。
PLACE_ODDS_FEATURES: tuple[Feature, ...] = (
    Feature(PLACE_ODDS_LOW_FEATURE, "M", FeatureKind.NUMERIC, PredictionTiming.DAY_BEFORE),
    Feature(PLACE_ODDS_HIGH_FEATURE, "M", FeatureKind.NUMERIC, PredictionTiming.DAY_BEFORE),
    Feature(PLACE_MARKET_RATE, "M", FeatureKind.NUMERIC, PredictionTiming.DAY_BEFORE),
    Feature(PLACE_TO_WIN_RATIO, "M", FeatureKind.NUMERIC, PredictionTiming.DAY_BEFORE),
)
