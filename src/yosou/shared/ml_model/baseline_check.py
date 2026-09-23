"""モデルが基準を使って学んだかと、予測に渡す基準の取り出し。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .probability_model import FeatureData


@dataclass(frozen=True)
class BaselineCheck:
    """モデルが目的変数の基準（ロジット）を出発点にして学んだか（既存モデルの修正計画の 1・2）。

    基準を使って学んだモデルは、予測でも同じ基準を足さないと確率がずれる。予測用データに基準が無ければ
    （例: 前日のモデルに木曜のデータを渡した）、黙って続けずに止める。
    """

    uses_baseline: bool

    def values_of(self, data: FeatureData) -> np.ndarray:
        """``data`` の基準の値。基準を使って学んだのに ``data`` に基準が無ければ ``ValueError``。"""
        if data.baseline is None:
            raise ValueError(
                "このモデルはオッズから作った基準を出発点にして学んでいますが、渡されたデータに基準がありません。"
                "オッズが分かる時点（前日・当日）のデータを渡してください。"
            )
        return data.baseline.array()
