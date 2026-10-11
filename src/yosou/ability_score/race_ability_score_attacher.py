"""これから走る1レースの予測用データに、能力スコアを足す（予測の流れに渡す関数の形）。"""

from __future__ import annotations

from yosou.shared.dataset import OddsInput, PredictionData
from yosou.shared.feature import PredictionTiming

from .ability_score_attachment import AbilityScoreAttachment


class RaceAbilityScoreAttacher:
    """全頭の予想の予測の流れ（``PredictionWorkflow``）の ``extras``・``win_extras`` に渡す関数の形（``attach``）。

    S の ``RaceScoreAttacher`` と同じ形だが、元DB もモデルも要らない（予測用データの能力指数と斤量から作る）。
    レースID・時点・オッズは、ほかの材料と同じ形で受け取るだけで使わない。
    """

    def __init__(self) -> None:
        self._attachment = AbilityScoreAttachment()

    def attach(self, data: PredictionData, race_id: str, timing: PredictionTiming, given: OddsInput | None) -> PredictionData:
        return self._attachment.apply(data)
