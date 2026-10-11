"""これから走る1レースの予測用データに、体重の割引を足す（予測の流れに渡す関数の形）。"""

from __future__ import annotations

from yosou.shared.dataset import OddsInput, PredictionData
from yosou.shared.feature import PredictionTiming

from .weight_discount_attachment import WeightDiscountAttachment
from .weight_table import WeightTable


class RaceWeightDiscountAttacher:
    """全頭の予想の予測の流れ（``PredictionWorkflow``）の ``extras``・``win_extras`` に渡す関数の形（``attach``）。

    表 W（``WeightTableStore`` のもの）を持ち、予測用データの増減（速報の馬体重を反映したもの）・前走からの日数・馬齢から引く。
    レースID・時点・オッズは、ほかの材料と同じ形で受け取るだけで使わない。
    """

    def __init__(self, table: WeightTable) -> None:
        self._attachment = WeightDiscountAttachment(table)

    def attach(self, data: PredictionData, race_id: str, timing: PredictionTiming, given: OddsInput | None) -> PredictionData:
        return self._attachment.apply(data)
