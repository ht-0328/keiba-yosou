"""レースの条件で学習データを分ける実験の、区分の列。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 主場（東京・中山・京都・阪神）。それ以外はローカル。
_MAIN_VENUES = frozenset({"東京", "中山", "京都", "阪神"})
#: 区分の列の名前。
SURFACE = "区分: 芝ダ"
VENUE_GROUP = "区分: 競馬場（主場・ローカル）"
DISTANCE_BAND = "区分: 距離帯"
SURFACE_DISTANCE = "区分: 芝ダ×距離帯"
FIELD_BAND = "区分: 頭数帯"
CONDITION_COLUMNS: tuple[str, ...] = (SURFACE, VENUE_GROUP, DISTANCE_BAND, SURFACE_DISTANCE, FIELD_BAND)


class ConditionColumns:
    """学習データを条件で分ける実験（既存モデルの修正計画の 2「競馬場・距離などの違い」）の、区分の列を作る。

    芝ダ、競馬場（主場 = 東京・中山・京都・阪神 か ローカル）、距離帯（〜1400m・1401〜1800m・1801〜2200m・2201m〜）、
    芝ダ × 距離帯、頭数帯（〜10頭・11〜15頭・16頭〜）。特徴量の表（芝ダ・競馬場・距離・出走頭数の列）から作る。
    """

    def build(self, features: pd.DataFrame) -> pd.DataFrame:
        distance = pd.to_numeric(features["距離"], errors="coerce")
        field = pd.to_numeric(features["出走頭数"], errors="coerce")
        surface = features["芝ダ"].astype(str)
        band = pd.Series(np.select([distance <= 1400, distance <= 1800, distance <= 2200],
                                   ["〜1400m", "1401〜1800m", "1801〜2200m"], default="2201m〜"), index=features.index)
        return pd.DataFrame({
            SURFACE: surface,
            VENUE_GROUP: np.where(features["競馬場"].isin(_MAIN_VENUES), "主場", "ローカル"),
            DISTANCE_BAND: band,
            SURFACE_DISTANCE: surface + "・" + band,
            FIELD_BAND: np.select([field <= 10, field <= 15], ["〜10頭", "11〜15頭"], default="16頭〜"),
        }, index=features.index)
