"""年ごとの確かめの結果の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestReport:
    """年ごとの確かめの結果（設計書 16 の 7 の表1〜4）。

    - ``returns``: 買い方 × 券種 × 年（と合計）の、的中率・回収率など（``ReturnSummary`` の表）。
    - ``finish``: ⑦ の年ごとの当たり具合（``FinishYearMetrics`` の表）。
    - ``stages``: ①〜⑥ の年ごとの当たり具合（``StageYearMetrics`` の縦長の表）。
    - ``calibration``: 3着以内の確率の帯ごとの実際の割合（``PlaceCalibration`` の表）。
    - ``order_lambdas``: 年 → ⑦ のならしの指数 λ。
    - ``years``: 確かめた年。``settings``: 学習に使った設定（表に書く）。
    """

    returns: pd.DataFrame
    finish: pd.DataFrame
    stages: pd.DataFrame
    calibration: pd.DataFrame
    order_lambdas: dict[str, float]
    years: tuple[int, ...]
    settings: dict
