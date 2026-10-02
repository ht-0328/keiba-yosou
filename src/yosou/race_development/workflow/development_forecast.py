"""1レースの予測の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.feature import PredictionTiming


@dataclass(frozen=True)
class DevelopmentForecast:
    """1レースの予測（設計書 04 の「workflow/」）。

    - ``horses``: 1行 = 1頭（馬番・馬名・印・1着・2着以内・3着以内の確率・先頭の確率・先団・中団・後方の確率・
      4コーナーの位置の予測・上がりの速さの予測）。1着の確率の高い順。
    - ``race``: 1行（ハイ・平均・スローの確率、前半タイムと後半タイムの予測の秒数（真ん中と、80% が入る幅））。
    - ``tickets``: 券種ごとの、印どおりの買い目（1点 100円）。
    """

    race_id: str
    timing: PredictionTiming
    horses: pd.DataFrame
    race: pd.DataFrame
    tickets: pd.DataFrame
