"""逃げたい馬の数え方が、実際のペースをどれだけ当てるか。"""

from __future__ import annotations

import pandas as pd
from sklearn.metrics import roc_auc_score

from ..pace import HIGH, SLOW

#: 出力の列。
COLUMNS: tuple[str, ...] = ("順位相関", "ハイとスローの見分け（AUC）", "少ない組のハイ率", "多い組のハイ率", "少ない組のスロー率", "多い組のスロー率")


class LeaderPaceScore:
    """レースの表（数え方の列と、z と区分の列を持つ）で、数え方 ``count_column`` の当たり具合を出す。

    - 順位相関: 数と前半の速さ（z）の Spearman の順位相関。1 に近いほど、数が多いほど速い。
    - ハイとスローの見分け（AUC）: ハイとスローのレースだけで、数でハイを見分けられるか。0.5 は当てずっぽう、1 は完全。
    - 少ない組・多い組: 数の小さい方から3分の1と、大きい方から3分の1のレースの、ハイとスローの割合（%）。
      同じ値が多くて3分の1に切れないときは、値で切る（例: 0頭の組と、2頭以上の組）。
    """

    def score(self, races: pd.DataFrame, count_column: str, z_column: str, pace_column: str) -> dict[str, float]:
        count = races[count_column]
        correlation = count.corr(races[z_column], method="spearman")
        decided = races[races[pace_column].isin((HIGH, SLOW))]
        auc = roc_auc_score(decided[pace_column] == HIGH, decided[count_column])
        low, high = count.quantile(1 / 3), count.quantile(2 / 3)
        few = races[count <= low]
        many = races[count > high] if (count > high).any() else races[count >= high]
        return dict(zip(COLUMNS, (correlation, auc, self._share(few, pace_column, HIGH), self._share(many, pace_column, HIGH),
                                  self._share(few, pace_column, SLOW), self._share(many, pace_column, SLOW))))

    def _share(self, races: pd.DataFrame, pace_column: str, pace: str) -> float:
        return float((races[pace_column] == pace).mean() * 100)
