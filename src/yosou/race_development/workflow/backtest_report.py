"""年ごとの確かめの結果の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.feature import PredictionTiming


@dataclass(frozen=True)
class BacktestReport:
    """年ごとの確かめの結果（設計書 16 の 4・7 の表1〜6）。

    - ``returns``: 買い方 × 券種 × 年（と合計）の、的中率・回収率など（``ReturnSummary`` の表）。
    - ``finish``: ⑦ の年ごとの当たり具合（``FinishYearMetrics`` の表）。
    - ``stages``: ①〜⑥ の年ごとの当たり具合（``StageYearMetrics`` の縦長の表）。
    - ``calibration``: 3着以内の確率の帯ごとの実際の割合（``PlaceCalibration`` の表）。
    - ``order_lambdas``: 年 → ⑦ のならしの指数 λ。
    - ``line_totals``・``chosen_lines``・``allocation``: 買い方 → 期待値の線と券種の配分の表（``ValueLineChoice``）。
      買い方は「モデル」と「オッズ入り」（オッズを足した ⑦。当日の時点だけ）。
    - ``unlabeled``: 正解を作らなかったレースの、理由ごと・条件ごとの割合（``UnlabeledRaceTable``）。
      ``unlabeled_examples``: 先頭が決まらないレースのレースID（通過順と照らし合わせる）。
    - ``years``: 確かめた年。``timing``: 予測した時点。``settings``: 学習に使った設定（表に書く）。
    """

    returns: pd.DataFrame
    finish: pd.DataFrame
    stages: pd.DataFrame
    calibration: pd.DataFrame
    order_lambdas: dict[str, float]
    line_totals: dict[str, pd.DataFrame]
    chosen_lines: dict[str, pd.DataFrame]
    allocation: dict[str, pd.DataFrame]
    unlabeled: pd.DataFrame
    unlabeled_examples: list[str]
    years: tuple[int, ...]
    timing: PredictionTiming
    settings: dict
