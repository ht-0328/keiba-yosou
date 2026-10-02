"""K の数え方の見直し: 過去の開催が少ないレースでは、重賞の傾向を基準どおり（0）にする。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.dataset import TrainingData
from yosou.stakes_tendency_top3.feature import K_FEATURES
from yosou.stakes_tendency_top3.feature.stakes_tendency_features import EDITIONS

#: 傾向を使う、過去の開催の数の下限。これより少ないレースのずれは、まぐれの割合が大きいとみて使わない。
MIN_EDITIONS = 5


class TendencyFloor:
    """保存した重賞の学習データの K のうち、ずれの列（「過去開催の数」以外の9個）を、過去の開催が ``MIN_EDITIONS`` 回未満の
    レースで 0 にした学習データを返す（重賞の設計書 15 の 9 の「K の数え方の見直し」）。

    今の K は n/(n+k) で縮めているが、開催が数回のレースでも少しずれが残る。開催が少ないレースでは基準に寄せきるほうが
    良いかを確かめる。ほかの列と行は変えない。
    """

    def apply(self, data: TrainingData) -> TrainingData:
        gaps = [feature.name for feature in K_FEATURES if feature.name != EDITIONS]
        few = data.features[EDITIONS] < MIN_EDITIONS
        features = data.features.copy()
        features.loc[few, gaps] = 0.0
        return replace(data, features=features)
