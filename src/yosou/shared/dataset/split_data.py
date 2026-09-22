"""時期で分けた3つのデータ。"""

from __future__ import annotations

from dataclasses import dataclass

from .training_data import TrainingData


@dataclass(frozen=True)
class SplitData:
    """学習データ・検証データ・テストデータ（設計書 02）。学習 → 検証 → テストの順に新しい。"""

    train: TrainingData
    valid: TrainingData
    test: TrainingData

    def parts(self) -> dict[str, TrainingData]:
        """名前（学習・検証・テスト）ごとのデータ。"""
        return {"学習": self.train, "検証": self.valid, "テスト": self.test}
