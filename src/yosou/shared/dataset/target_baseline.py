"""目的変数の基準を作るクラスに共通の決まり。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from ..feature import PredictionTiming


class TargetBaseline(Protocol):
    """目的変数の基準（ロジット）の作り方（既存モデルの修正計画の 1・2）。予想ごとに違う。

    この決まりを守るクラスを ``DatasetBuilder`` に渡すと、学習データと予測用データに基準が付く。
    渡さない予想（荒れ具合など）は、これまでどおり基準なしで学ぶ。
    """

    @property
    def known_from(self) -> PredictionTiming:
        """基準が分かる最初の時点（オッズから作るなら前日）。"""
        ...

    def build(self, entries: pd.DataFrame) -> pd.Series:
        """行ごとの基準のロジット。欠損値にしない。行の並びと index は ``entries`` と同じ。

        ``entries`` には、同じレースの出走馬が全頭入っている（オッズから作る基準は、ほかの馬のオッズも使う）。
        """
        ...
