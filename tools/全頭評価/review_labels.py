"""特徴量の分類と名前（今週の予想の部品に、特別登録の予想だけの材料の分類を足す）。"""

from __future__ import annotations

from 今週の予想.feature_labels import FeatureLabels

#: 能力スコア（T）の名前の頭。今週の予想の分類の決め方には無いので、ここで「能力」にする。
_ABILITY_SCORE_HEAD = "能力スコア"


class ReviewLabels(FeatureLabels):
    """今週の予想の ``FeatureLabels`` と同じ分類・名前で、能力スコア（T）を「能力」の分類にする。

    特別競走の印（Y）はレースの全馬に同じ値なので、そのまま「レースの条件」（強み・弱みに出さない）。
    """

    def category(self, name: str) -> str:
        if name.startswith(_ABILITY_SCORE_HEAD):
            return "能力"
        return super().category(name)
