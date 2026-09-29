"""YAML の target: 目的変数（モデルに当てさせる答えの列）を付ける。"""

import pandas as pd

from yosou.shared.feature.value_types import as_numbers


class BinaryTargetLabeler:
    """馬券内（3着以内）・馬券外（4着以下・中止・失格）・勝利（1着）を 1、それ以外を 0 にする。"""

    def labels(self, rows: pd.DataFrame, target: str) -> pd.DataFrame:
        finish = as_numbers(rows["finish"])
        top3 = finish.between(1, 3)
        labels = {"馬券内": top3, "馬券外": ~top3, "勝利": finish.eq(1)}
        return pd.DataFrame({target: labels[target].astype(int)}, index=rows.index)
