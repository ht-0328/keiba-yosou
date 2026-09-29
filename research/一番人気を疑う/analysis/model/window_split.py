"""1つの区切りの、学習・検証・テストの行を分ける。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from 既存モデルの改善.analysis.windows import TestWindow


@dataclass(frozen=True)
class WindowSplit:
    """研究「既存モデルの改善」と同じ区切り（``TestWindow``）で、1行 = 1頭の表を分ける。

    分けるのは開催日なので、同じレース・同じ日のレースが、学習とテストに分かれることはない。
    学習の始まりは表の始まり（表によって 2012年か 2017年）。
    """

    window: TestWindow

    def train(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame[frame["開催日"] < self.window.valid_first_day]

    def valid(self, frame: pd.DataFrame) -> pd.DataFrame:
        day = frame["開催日"]
        return frame[(day >= self.window.valid_first_day) & (day < self.window.test_first_day)]

    def test(self, frame: pd.DataFrame) -> pd.DataFrame:
        day = frame["開催日"]
        return frame[(day >= self.window.test_first_day) & (day <= self.window.test_last_day)]
