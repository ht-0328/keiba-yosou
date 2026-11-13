"""区切りごとに、そのテスト期間の始まりより前の WIN5 だけで配当の見積もりの式を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.form_aptitude_win5_tickets.payout import FEATURE_COLUMNS, PayoutEstimator, PayoutTrainingRows
from yosou.form_aptitude_win5_tickets.repository.win5_columns import PAYOUT, RACE_DATE


class Win5FoldEstimators:
    """設計書「近走と適性からWIN5の買い目を決める」11 の 8・16 の 1.。区切りごとに、テスト期間の始まりより前の WIN5 の当たり組だけで
    ``PayoutEstimator`` を作る（確かめる期間の払戻を式に入れない）。式の作り方は ``fit-payout`` と同じ部品（``PayoutTrainingRows``）。"""

    def of(self, history: pd.DataFrame, folds: pd.DataFrame) -> dict[str, PayoutEstimator]:
        """区切りの名前 → 式。``folds`` の列は fold・start（テスト期間の始まりの ``YYYY-MM-DD``）。"""
        return {str(fold): self._fit(history, str(start)) for fold, start in zip(folds["fold"], folds["start"], strict=True)}

    def _fit(self, history: pd.DataFrame, start: str) -> PayoutEstimator:
        rows = PayoutTrainingRows().of(history.loc[history[RACE_DATE] < start])
        return PayoutEstimator.fit(rows[list(FEATURE_COLUMNS)], rows[PAYOUT])
