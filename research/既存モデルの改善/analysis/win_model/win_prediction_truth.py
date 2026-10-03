"""保存した1着の予測に、答え（1着）・人気・オッズから見た勝率を付けて読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_ID, WIN
from yosou.shared.dataset.column_names import POPULARITY, WIN_ODDS
from yosou.shared.feature.odds import WIN_RATE

from ..walk_forward import PART, PART_TEST, PREDICTION_COLUMN, WINDOW, PredictionStore

#: 学習データの表から付ける列（表の部分 → 列）。特徴量の表は大きいので読まない。
_TRUTH_PARTS = {"ids": [RACE_ID, HORSE_ID], "evaluation": [POPULARITY, WIN_ODDS, WIN_RATE], "targets": [WIN]}
#: 1着のモデルの確率の列と、比べる相手（オッズから見た勝率）の列。
SCORE = "score"
MARKET_WIN = WIN_RATE


class WinPredictionTruth:
    """``<predictions>/<表>/<作り方>.pkl`` のテスト期間の行に、学習データの表（``<tables>/<表>/``）の答えと人気とオッズから見た勝率を付ける。

    列は ``レースID``・``馬ID``・``馬番``・``確定の単勝人気``・``確定の単勝オッズ``・``オッズから見た勝率``・``1着``・``score``（2つのモデルの平均）・``区切り``。
    答えの無い行（表に無い行）は落とす。
    """

    def __init__(self, tables: Path, predictions: Path) -> None:
        self._tables = Path(tables)
        self._store = PredictionStore(predictions)

    def read(self, table: str, key: str) -> pd.DataFrame:
        folder = self._tables / table
        parts = [pd.read_pickle(folder / f"{part}.pkl")[columns] for part, columns in _TRUTH_PARTS.items()]
        truth = pd.concat(parts, axis=1).drop_duplicates([RACE_ID, HORSE_ID])
        predictions = self._store.read(table, key)
        tests = predictions[predictions[PART] == PART_TEST]
        frame = tests[[RACE_ID, HORSE_ID, HORSE_NO, PREDICTION_COLUMN, WINDOW]].merge(truth, on=[RACE_ID, HORSE_ID], how="left")
        frame[RACE_ID] = frame[RACE_ID].astype(str)
        return frame.rename(columns={PREDICTION_COLUMN: SCORE}).dropna(subset=[WIN])
