"""速報の馬体重を、出走の行に反映する。"""

from __future__ import annotations

import pandas as pd


class AnnouncedWeightApplier:
    """速報の馬体重がある馬は、馬体重と増減をその値にする。無い馬は、出走の行の値のまま。"""

    def apply(self, entries: pd.DataFrame, announced_weights: pd.DataFrame) -> pd.DataFrame:
        """``announced_weights`` の列は ``horse_no``・``body_weight``・``weight_change``。"""
        announced = entries[["horse_no"]].merge(announced_weights, on="horse_no", how="left")
        announced.index = entries.index
        is_announced = announced["body_weight"].notna()
        return entries.assign(
            body_weight=entries["body_weight"].mask(is_announced, announced["body_weight"]),
            weight_change=entries["weight_change"].mask(is_announced, announced["weight_change"]),
        )
