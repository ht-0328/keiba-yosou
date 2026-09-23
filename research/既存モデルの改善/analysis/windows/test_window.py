"""1つの検証の区切り。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from yosou.shared.dataset import TrainingData


@dataclass(frozen=True)
class TestWindow:
    """1つの検証の区切り。学習 → 検証 → テストの順に新しい。

    - 学習: 学習データの始まり（2017年1月）から、検証の始まりの前日まで。モデルはここで学ぶ。
    - 検証: テストの直前の半年。木を足すのを止める判断（早期終了）と、確率の調整・買う線・危険の線を決めるのに使う。
    - テスト: 評価する半年。ここの結果は、どの線を決めるのにも使わない。

    ``name`` は表に出す名前（例 2023年前半）。``test_last_day`` はテストの最後の日（その日を含む）。
    """

    # 名前が Test で始まるので、pytest がテストのクラスと間違えて集めないようにする
    __test__ = False

    name: str
    valid_first_day: date
    test_first_day: date
    test_last_day: date

    def __post_init__(self) -> None:
        if not (self.valid_first_day < self.test_first_day <= self.test_last_day):
            raise ValueError(f"区切りの日の順が違います: {self}")

    def train(self, data: TrainingData) -> TrainingData:
        """学習に使う行（検証の始まりより前）。"""
        return data.between(None, self.valid_first_day)

    def valid(self, data: TrainingData) -> TrainingData:
        """検証に使う行（テストの直前の半年）。"""
        return data.between(self.valid_first_day, self.test_first_day)

    def test(self, data: TrainingData) -> TrainingData:
        """テストの行。"""
        return data.between(self.test_first_day, self.test_last_day + timedelta(days=1))
