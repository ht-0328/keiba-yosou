"""3着以内のモデル用のデータを、1着のモデル用に持ち替える。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from .baseline_logit import BaselineLogit
from .column_names import RACE_ID, WIN_ODDS
from .prediction_data import PredictionData
from .top3_target_builder import WIN
from .training_data import TrainingData
from .win_baseline import WinBaseline


class WinTargetData:
    """3着以内のモデル用に作った学習データ・予測用データを、1着のモデル用に持ち替える（近走と適性の予想の設計書 10・15 の 14）。

    目的変数を「1着」に、基準をオッズから見た勝率のロジット（``WinBaseline``）に替える。特徴量はそのまま。
    基準の元の単勝オッズは、学習データでは評価用の列、予測用データでは ``market``（予測に使ったオッズ）から取る。
    基準はオッズの分かる前日から（オッズの無い時点の予測用データでは None）。
    """

    def __init__(self) -> None:
        self._baseline = WinBaseline()

    def training(self, data: TrainingData) -> TrainingData:
        labeled = data.with_label(WIN)
        return replace(labeled, baseline=self._logit(labeled.ids, labeled.evaluation[WIN_ODDS]))

    def prediction(self, data: PredictionData) -> PredictionData:
        if data.market is None or WIN_ODDS not in data.market.columns:
            return replace(data, baseline=None)
        return replace(data, baseline=self._logit(data.ids, data.market[WIN_ODDS]).for_timing(data.timing))

    def _logit(self, ids: pd.DataFrame, win_odds: pd.Series) -> BaselineLogit:
        """同じレースの全頭の行から、オッズから見た勝率のロジットを作る。"""
        entries = pd.DataFrame({"race_id": ids[RACE_ID].to_numpy(), "win_odds": win_odds.to_numpy()}, index=ids.index)
        return BaselineLogit(self._baseline.build(entries), self._baseline.known_from)
