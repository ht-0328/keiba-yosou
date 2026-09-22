"""学習データを時期で3つに分ける。"""

from __future__ import annotations

from .split_data import SplitData
from .training_data import TrainingData
from .training_period import TrainingPeriod


class PeriodSplitter:
    """学習データを開催日で、学習データ・検証データ・テストデータに分ける。

    分け方は設計書でまだ決まっていない（「次の設計書」）。いまは仮に、期間の2つの区切りの日で3つに分ける。
    学習 = 検証データの始まりより前、検証 = そこからテストデータの始まりの前日まで、テスト = それ以降。
    """

    def __init__(self, period: TrainingPeriod) -> None:
        self._period = period

    def split(self, data: TrainingData) -> SplitData:
        """学習データを3つに分ける。どれかが空なら ``ValueError``。"""
        valid_first_day, test_first_day = self._period.valid_first_day, self._period.test_first_day
        split = SplitData(
            train=data.between(None, valid_first_day),
            valid=data.between(valid_first_day, test_first_day),
            test=data.between(test_first_day, None),
        )
        empty_names = [name for name, part in split.parts().items() if len(part) == 0]
        if empty_names:
            raise ValueError(
                f"{'・'.join(empty_names)}データが空です。区切りの日（検証 {valid_first_day}・"
                f"テスト {test_first_day}）と、DB に入っている期間を確かめてください。"
            )
        return split
