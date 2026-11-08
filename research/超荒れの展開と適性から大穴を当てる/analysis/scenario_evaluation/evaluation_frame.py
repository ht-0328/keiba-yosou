"""確かめの表の元: テストの半年の行に、新しい予想と比べる相手の確率・市場の率・目的変数を並べた表（1行 = 1頭）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

#: 新しい予想の名前と、期間の分け方（探索 2019〜2024年・確認 2025年から）。
NEW = "展開の型で混ぜる"
EXPLORE, CONFIRM = "探索（2019〜2024年）", "確認（2025年から）"
CONFIRM_FROM = pd.Timestamp("2025-01-01")
_KEYS = ["レースID", "馬番"]


@dataclass(frozen=True)
class EvaluationFrame:
    """``top3``・``win`` は新しい予想の予測の表（``ScenarioWindowTrainer`` の形）、``comparisons`` は（相手, 目的変数）→ pkl。

    列: race_id・horse_no・race_date・popularity・period・y_top3・y_win・m_top3・m_win（オッズから見た率）・
    ``p_<目的変数>_<相手>``（新しい予想は ``NEW``）・新しい予想の展開の型ごとの確率 s_top3_0〜2・s_win_0〜2。テストの行だけ。"""

    top3: pd.DataFrame
    win: pd.DataFrame
    comparisons: dict[tuple[str, str], Path]

    def build(self) -> pd.DataFrame:
        top3, win = self._tested(self.top3), self._tested(self.win)
        frame = top3[[*_KEYS, "開催日", "人気", "目的変数", "オッズから見た率", "確率", "確率_スロー", "確率_平均", "確率_ハイ"]].rename(
            columns={"目的変数": "y_top3", "オッズから見た率": "m_top3", "確率": f"p_top3_{NEW}",
                     "確率_スロー": "s_top3_0", "確率_平均": "s_top3_1", "確率_ハイ": "s_top3_2"})
        frame = frame.merge(win[[*_KEYS, "目的変数", "オッズから見た率", "確率", "確率_スロー", "確率_平均", "確率_ハイ"]].rename(
            columns={"目的変数": "y_win", "オッズから見た率": "m_win", "確率": f"p_win_{NEW}",
                     "確率_スロー": "s_win_0", "確率_平均": "s_win_1", "確率_ハイ": "s_win_2"}), on=_KEYS, how="inner")
        for (name, target), path in self.comparisons.items():
            other = self._tested(pd.read_pickle(path))[[*_KEYS, "確率"]].rename(columns={"確率": f"p_{target}_{name}"})
            frame = frame.merge(other.drop_duplicates(_KEYS), on=_KEYS, how="left")
        frame = frame.rename(columns={"レースID": "race_id", "馬番": "horse_no", "開催日": "race_date", "人気": "popularity"})
        frame["race_id"] = frame["race_id"].astype(str)
        frame["period"] = np.where(pd.to_datetime(frame["race_date"]) >= CONFIRM_FROM, CONFIRM, EXPLORE)
        return frame

    @staticmethod
    def _tested(table: pd.DataFrame) -> pd.DataFrame:
        tested = table.loc[table["期間"] == "テスト"] if "期間" in table else table
        return tested.astype({"レースID": str}).astype({"馬番": int})
