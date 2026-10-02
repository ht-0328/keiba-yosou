"""予測の結果と、その理由の材料。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.feature import PredictionTiming


@dataclass(frozen=True)
class ExplainedPrediction:
    """1レースの予測の結果（``PredictionWorkflow.run`` と同じ表）に、理由を見せるための材料を添えたもの。

    - ``table``: 予測の結果の表（ID 列・単勝オッズ・3着以内に入る確率・モデルごとの確率・オッズから見た3着以内率・複勝の期待値）。
    - ``features``: モデルに渡した特徴量の値（行と index は ``table`` と同じ）。
    - ``contributions``: 特徴量ごとの寄与（2つのモデルの平均。ロジットの上げ下げ。行と index は ``table`` と同じ）。
    - ``timing``: 予測した時点。``pool_free`` は、当日に券種のオッズが無く、N を使わないモデルで予測したか。
    """

    table: pd.DataFrame
    features: pd.DataFrame
    contributions: pd.DataFrame
    timing: PredictionTiming
    pool_free: bool = False
