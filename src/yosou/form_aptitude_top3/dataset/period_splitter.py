"""学習データを時期で3つに分ける。"""

from __future__ import annotations

from datetime import date

from .split_data import SplitData
from .training_data import TrainingData

#: 検証データの最初の開催日（仮）。これより前が学習データ。
VALID_FIRST_DAY = date(2025, 7, 1)
#: テストデータの最初の開催日（仮）。検証データはこの前日まで。
TEST_FIRST_DAY = date(2026, 1, 1)


class PeriodSplitter:
    """学習データを開催日で、学習データ・検証データ・テストデータに分ける。

    分け方は設計書でまだ決まっていない（「次の設計書」）。いまは仮に、2つの区切りの日で3つに分ける。
    学習 = ``valid_first_day`` より前、検証 = それから ``test_first_day`` の前日まで、テスト = それ以降。
    """

    def __init__(self, valid_first_day: date = VALID_FIRST_DAY,
                 test_first_day: date = TEST_FIRST_DAY) -> None:
        if valid_first_day >= test_first_day:
            raise ValueError(
                f"検証データの最初の日（{valid_first_day}）は、"
                f"テストデータの最初の日（{test_first_day}）より前にしてください"
            )
        self._valid_first_day = valid_first_day
        self._test_first_day = test_first_day

    def split(self, data: TrainingData) -> SplitData:
        """学習データを3つに分ける。どれかが空なら ``ValueError``。"""
        split = SplitData(
            train=data.between(None, self._valid_first_day),
            valid=data.between(self._valid_first_day, self._test_first_day),
            test=data.between(self._test_first_day, None),
        )
        empty_names = [name for name, part in split.parts().items() if len(part) == 0]
        if empty_names:
            raise ValueError(
                f"{'・'.join(empty_names)}データが空です。区切りの日（検証 {self._valid_first_day}・"
                f"テスト {self._test_first_day}）と、DB に入っている期間を確かめてください。"
            )
        return split
