"""予想した確率と、実際に 1 になった割合を、確率の帯ごとに並べる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 確率の帯の区切り（帯は「左より大きく、右以下」）。穴馬の3着以内の確率は 0.02〜0.4 あたりに集まるので、そこを細かく切る。
BANDS: tuple[float, ...] = (0.0, 0.02, 0.05, 0.08, 0.12, 0.16, 0.2, 0.25, 0.3, 0.4, 1.0)
#: 表の列の名前。
BAND, COUNT, PREDICTED, ACTUAL, RATIO = "確率の帯", "頭数", "予想の平均", "実際の割合", "実際 ÷ 予想"


class ProbabilityBands:
    """予想した確率が、実際に 1 になった割合と合っているか（確率のずれ）を、確率の帯ごとに測る（穴馬の設計書 16 の 4）。

    例: 確率 0.12〜0.16 の帯の馬が 1,000頭いて、予想の平均が 0.14、実際に3着以内に入ったのが 150頭なら、
    実際の割合は 0.15、「実際 ÷ 予想」は 1.07 で、その帯はやや低めに見積もっている。1 より小さければ高めに見積もっている。

    ``gap()`` は、帯ごとの |予想の平均 − 実際の割合| を頭数で重み付けして平均した値（期待較正誤差、ECE）。
    0 に近いほど、確率がそのまま「その割合で起きる」と読める。
    """

    def table(self, label: pd.Series, probability: pd.Series) -> pd.DataFrame:
        """帯ごとの行（``BAND``・``COUNT``・``PREDICTED``・``ACTUAL``・``RATIO``）。馬のいない帯は出さない。"""
        runners = pd.DataFrame({PREDICTED: probability.to_numpy(dtype="float64"),
                                ACTUAL: label.to_numpy(dtype="float64")})
        band = pd.cut(runners[PREDICTED], BANDS, include_lowest=True)
        grouped = runners.groupby(band, observed=True)
        summary = grouped.mean().assign(**{COUNT: grouped.size()})
        summary[RATIO] = summary[ACTUAL] / summary[PREDICTED].where(summary[PREDICTED] > 0)
        summary[BAND] = [f"{interval.left:g}〜{interval.right:g}" for interval in summary.index]
        return summary.reset_index(drop=True)[[BAND, COUNT, PREDICTED, ACTUAL, RATIO]]

    def gap(self, label: pd.Series, probability: pd.Series) -> float:
        """帯ごとのずれを頭数で重み付けした平均（ECE）。馬が1頭もいなければ NaN。"""
        rows = self.table(label, probability)
        if rows.empty:
            return float("nan")
        return float(np.average((rows[PREDICTED] - rows[ACTUAL]).abs(), weights=rows[COUNT]))
