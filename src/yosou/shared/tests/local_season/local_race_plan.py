"""地方のレース1つの条件。"""

from __future__ import annotations

from dataclasses import dataclass

from ..synthetic_season.race_plan import RacePlan

#: 地方のトラックコード。24 = ダート・右（大井）。
LOCAL_DIRT_TRACK = "24"


@dataclass(frozen=True)
class LocalRacePlan(RacePlan):
    """地方のレース1つの条件。中央の ``RacePlan`` に、クラスを表す競走条件名称（``condition_name``）を足したもの。"""

    condition_name: str = ""
