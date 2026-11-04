"""地方の当日の馬場傾向（U）の特徴量の一覧。名前は中央と同じ5個で、当日から分かる。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.feature import Feature, PredictionTiming
from yosou.track_bias import TRACK_BIAS_FEATURES

#: U. 当日の馬場傾向（5個。どれも数値）。使う内の傾き・使う前の傾き（レースの値）と、馬ごとの内の分・前の分・その和（補正 B）。
#: 中央は前日から数える（前の日の同じ馬場のレース）が、地方は当日の先に終わったレースを数える当日だけに足す（地方の設計書 07・15 の 11）。
LOCAL_TRACK_BIAS_FEATURES: tuple[Feature, ...] = tuple(
    replace(feature, known_from=PredictionTiming.RACE_DAY) for feature in TRACK_BIAS_FEATURES
)
