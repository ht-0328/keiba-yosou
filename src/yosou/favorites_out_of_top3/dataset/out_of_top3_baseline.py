"""目的変数「4着以下」の基準を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import Top3Baseline
from yosou.shared.feature import PredictionTiming


class OutOfTop3Baseline:
    """4着以下の基準 = オッズから見た4着以下の確率（1 − オッズから見た3着以内率）のロジット。``TargetBaseline`` を守る。

    ロジットは裏返すと符号が変わるだけなので、3着以内の基準（``Top3Baseline``）の符号を変えて作る。
    例: オッズから見た3着以内率 0.70 の1番人気なら、4着以下の基準は 0.30。モデルは「この馬は、同じオッズの馬より
    どれだけ負けやすいか」だけを学ぶ（既存モデルの修正計画の 1「人気馬の4着以下」）。
    """

    def __init__(self) -> None:
        self._top3 = Top3Baseline()

    @property
    def known_from(self) -> PredictionTiming:
        return self._top3.known_from

    def build(self, entries: pd.DataFrame) -> pd.Series:
        return -self._top3.build(entries)
