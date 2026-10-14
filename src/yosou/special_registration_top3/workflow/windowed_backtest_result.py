"""7つの区切りでの確かめの結果の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from yosou.shared.evaluation import Evaluation


@dataclass(frozen=True)
class WindowedBacktestResult:
    """7つの区切りでの確かめの結果。

    - ``special``: 目的変数 → [(区切りの名前か「全期間」, 特別競走の行の当たり具合)]。
    - ``all_rows``: 目的変数 → [(区切りの名前, 全レースの行の当たり具合。参考)]。
    - ``prediction_paths``: 目的変数 → 書いた予測の表（道具「印の成績」が読む形。区切りの列付き）。
    - ``comparisons``: 目的変数 → 木曜のモデルとの比べ（``--compare`` を渡したときだけ）。
    - ``feature_count``: 学んだ特徴量の数。``variant``: 材料の版の名前。
    """

    special: dict[str, list[tuple[str, list[Evaluation]]]]
    all_rows: dict[str, list[tuple[str, list[Evaluation]]]]
    prediction_paths: dict[str, Path]
    feature_count: int
    variant: str
    comparisons: dict[str, pd.DataFrame] = field(default_factory=dict)
