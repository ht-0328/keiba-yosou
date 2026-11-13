"""その日に先に終わったレースの傾き（内外・前後）を、レースごとに出す（当日の時点で分かる馬場の傾向）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

#: 道具「トラックバイアス」がとっておくレースごとの傾きの表（Git の対象外）。
DEFAULT_SLOPES = Path(__file__).resolve().parents[4] / "reports" / "トラックバイアス" / "cache" / "傾き.pkl"
_DAY = ["race_date", "venue_code", "surface"]


@dataclass(frozen=True)
class PriorRaceBias:
    """傾きの表（race_id・race_date・venue_code・surface・race_no・内の傾き・前の傾き）から、同じ日・同じ競馬場・同じ芝ダで、
    そのレースより前に終わったレースの傾きの平均を出す。列は race_id・prior_inner・prior_front・prior_races（先に終わったレースの数）。
    その日の最初のレースは、先に終わったレースが無いので欠損値。傾きは正なら内（前）が市場の見立てより来ている。"""

    def of(self, slopes: pd.DataFrame) -> pd.DataFrame:
        frame = slopes.sort_values([*_DAY, "race_no"], kind="stable").reset_index(drop=True)
        keys = [frame[column] for column in _DAY]
        result = pd.DataFrame({"race_id": frame["race_id"].astype(str)})
        result["prior_races"] = frame.groupby(_DAY, sort=False).cumcount().astype(float)
        for source, target in (("内の傾き", "prior_inner"), ("前の傾き", "prior_front")):
            value = frame[source].fillna(0.0)
            seen = frame[source].notna().astype(float)
            total = value.groupby(keys, sort=False).cumsum() - value
            known = seen.groupby(keys, sort=False).cumsum() - seen
            result[target] = (total / known).where(known > 0)
        return result

    @staticmethod
    def load(path: Path = DEFAULT_SLOPES) -> pd.DataFrame:
        return pd.read_pickle(path)
