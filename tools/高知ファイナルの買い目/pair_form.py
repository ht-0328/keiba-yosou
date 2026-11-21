"""馬と騎手の組み合わせの、今回より前の騎乗数と3着以内率。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class PairForm:
    """``hj_n``・``hj_top3`` はその騎手で走った数と3着以内率、``h_n``・``h_top3`` はその馬の全部の走の数と3着以内率、
    ``hj_lift`` は2つの3着以内率の差（その騎手のときに良いか）、``hj_share`` はその騎手で走った割合。"""

    def build(self, d: pd.DataFrame) -> pd.DataFrame:
        d = d.sort_values(["horse_id", "race_date", "race_no"]).copy()
        pair = d.groupby(["horse_id", "jockey_code"])
        d["hj_n"] = pair.cumcount().astype(float)
        d["hj_top3"] = (pair["top3"].cumsum() - d["top3"]) / d["hj_n"].replace(0, np.nan)
        horse = d.groupby("horse_id")
        d["h_n"] = horse.cumcount().astype(float)
        d["h_top3"] = (horse["top3"].cumsum() - d["top3"]) / d["h_n"].replace(0, np.nan)
        d["hj_lift"] = d["hj_top3"] - d["h_top3"]
        d["hj_share"] = d["hj_n"] / d["h_n"].replace(0, np.nan)
        return d
