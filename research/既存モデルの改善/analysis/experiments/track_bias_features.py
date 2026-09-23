"""当日の、同じ競馬場・芝ダで先に終わったレースの傾向。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 特徴量の名前。
EARLIER_RACES = "当日の先に終わったレースの数"
FRONT_BIAS = "当日の上位馬の4角の位置の平均"
INSIDE_BIAS = "当日の上位馬の馬番の位置の平均"
OWN_POSITION = "馬番の位置"
NAMES: tuple[str, ...] = (EARLIER_RACES, FRONT_BIAS, INSIDE_BIAS, OWN_POSITION)
#: 同じ日・同じ競馬場・同じ芝ダを1つにまとめる鍵。
_DAY_KEY = ["race_date", "venue_code", "surface"]


class TrackBiasFeatures:
    """当日の馬場傾向（既存モデルの修正計画の 4「当日のそれまでのレースから分かる馬場傾向」）。

    同じ日・同じ競馬場・同じ芝ダで、先に終わったレース（レース番号が小さい）の3着以内の馬が、4コーナーでどのくらい前に
    いたか（4角の順位 ÷ 頭数。0 に近いほど前）と、どのくらい内の馬番だったか（馬番 ÷ 頭数）の平均。
    例: 午前のダートで逃げ・先行ばかり残っていれば、4角の位置の平均が小さい。その日の最初のレースは欠損値。
    馬の側の値として、自分の馬番の位置も足す（決定木が、内枠有利の日の内枠、を組み合わせられるように）。
    """

    def build(self, history: pd.DataFrame) -> pd.DataFrame:
        """列は race_id・horse_id と ``NAMES``。"""
        races = self._race_summary(history)
        earlier = self._earlier_means(races)
        position = pd.to_numeric(history["horse_no"], errors="coerce") / pd.to_numeric(history["field_size"], errors="coerce")
        runners = history[["race_id", "horse_id"]].assign(**{OWN_POSITION: position})
        return runners.merge(earlier, on="race_id", how="left")[["race_id", "horse_id", *NAMES]]

    def _race_summary(self, history: pd.DataFrame) -> pd.DataFrame:
        """レースごとの、3着以内の馬の4角の位置と馬番の位置の平均。"""
        field = pd.to_numeric(history["field_size"], errors="coerce")
        top = history.assign(
            corner=pd.to_numeric(history["corner4"], errors="coerce") / field,
            inside=pd.to_numeric(history["horse_no"], errors="coerce") / field,
        )
        top = top[pd.to_numeric(top["finish"], errors="coerce").between(1, 3)]
        summary = top.groupby("race_id").agg(corner=("corner", "mean"), inside=("inside", "mean"))
        keys = history.drop_duplicates("race_id").set_index("race_id")[[*_DAY_KEY, "race_no"]]
        return keys.join(summary).reset_index()

    def _earlier_means(self, races: pd.DataFrame) -> pd.DataFrame:
        """同じ日・競馬場・芝ダで、自分より前のレースだけの平均（自分のレースは入れない）。"""
        ordered = races.assign(race_no=pd.to_numeric(races["race_no"], errors="coerce")).sort_values([*_DAY_KEY, "race_no"])
        grouped = ordered.groupby(_DAY_KEY, sort=False)
        count = grouped.cumcount()
        corner_sum = grouped["corner"].cumsum() - ordered["corner"].fillna(0)
        inside_sum = grouped["inside"].cumsum() - ordered["inside"].fillna(0)
        return pd.DataFrame({
            "race_id": ordered["race_id"], EARLIER_RACES: count.astype(float),
            FRONT_BIAS: (corner_sum / count).where(count > 0, np.nan),
            INSIDE_BIAS: (inside_sum / count).where(count > 0, np.nan),
        })
