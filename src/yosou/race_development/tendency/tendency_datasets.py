"""既存の予想ごとの学習データの束。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from yosou.shared.dataset import TrainingData

from .tendency_source import TendencySource


@dataclass(frozen=True)
class TendencyDatasets:
    """既存の4つの予想の学習データ（それぞれの予想の ``dataset_builder`` で作ったもの）。

    既存の予想は、行の選び方（人気馬だけ・穴馬だけ・1レース1行）と特徴量（オッズを含む）と基準が、展開の予想とは違うので、
    展開の予想の1頭ごと・1レースごとの学習データとは別に持つ。
    """

    tables: Mapping[TendencySource, TrainingData]

    def of(self, source: TendencySource) -> TrainingData:
        return self.tables[source]

    def sizes(self) -> dict[str, int]:
        """既存の予想 → 行数（年ごとの予測を作った条件の文字列に入れる）。"""
        return {source.value: len(data) for source, data in self.tables.items()}
