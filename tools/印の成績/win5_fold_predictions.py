"""WIN5 の確かめに使う、当日と前日の区切りごとの1着の予測（テスト期間の行だけ）を表す値。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Win5FoldPredictions:
    """``race_day``・``day_before`` は今のモデルと同じ作りの当日・前日の1着の予測のテスト期間の行（列は race_id・race_date・horse_no・
    probability・fold。probability は LightGBM と CatBoost の平均）。``folds`` は区切りごとのテスト期間（列は fold・start・end。
    開催日の ``YYYY-MM-DD``）で、前日と当日の両方の予測がある区切りだけ。"""

    race_day: pd.DataFrame
    day_before: pd.DataFrame
    folds: pd.DataFrame

    def fold_of(self, race_date: str) -> str | None:
        """開催日を含む区切りの名前。どの区切りのテスト期間にも入らなければ None。"""
        found = self.folds.loc[(self.folds["start"] <= race_date) & (race_date <= self.folds["end"]), "fold"]
        return str(found.iloc[0]) if not found.empty else None
