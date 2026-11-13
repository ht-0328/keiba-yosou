"""出走ごとに、人気から見た期待の率（同じ重量種別・同じ頭数の帯で、同じ人気の馬がふつう出す3着以内率と1着率）を付ける。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 頭数の帯（同じ 10番人気でも、10頭立てと 18頭立てでは来る率が違うので分ける）。
FIELD_BANDS = ([0, 12, 15, 18], ["〜12頭", "13〜15頭", "16〜18頭"])


@dataclass(frozen=True)
class ExpectedRates:
    """``runs`` 全体（2015年からの平地）で、重量種別 × 頭数の帯 × 単勝人気 ごとの3着以内率と1着率を数え、
    ``expected_top3``・``expected_win`` として付ける（``field_band`` も足す）。``top3``・``won`` の列が要る。

    人気から見た差 = 実際の率 − この期待の率。比べる組ごとに人気・頭数・重量種別の混ざり方が違うので、組どうしはこの差で比べる。
    """

    def add(self, runs: pd.DataFrame) -> pd.DataFrame:
        frame = runs.copy()
        edges, labels = FIELD_BANDS
        frame["field_band"] = pd.cut(frame["field_size"], edges, labels=labels).astype(str)
        keys = [frame["weight_type"], frame["field_band"], frame["popularity"]]
        frame["expected_top3"] = frame["top3"].groupby(keys, dropna=False).transform("mean")
        frame["expected_win"] = frame["won"].groupby(keys, dropna=False).transform("mean")
        return frame
