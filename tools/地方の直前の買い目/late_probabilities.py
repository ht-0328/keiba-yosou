"""直前の買い目の材料にする、全頭の予想の確率（当日の時点と、オッズを使わない出馬表の時点）を1レースぶん出す。"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from yosou.local_form_aptitude_top3.command.predict_command import PredictCommand
from yosou.shared.feature import PredictionTiming
from yosou.shared.workflow import PROBABILITY, WIN_PROBABILITY

from .late_columns import HORSE_NO, TOP3_FREE, TOP3_MODEL, WIN_FREE, WIN_MODEL

#: 2つのモデルを学んだときと同じ全頭の予想のモデル（学習用の表の予想と同じ作り。本番の通知のモデルとは別）。
PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_MODELS = PROJECT / "reports" / "地方競馬の近走と適性から3着以内を予想" / "models-2024検証"
_HORSE_NO = "馬番"


class LateProbabilities:
    """予想は地方の予想モデルの ``PredictCommand.prediction`` を、時点を変えて2回呼ぶ（同じ接続なので事実表を作るのは1回）。
    当日の時点は、元DB のいちばん新しい断面の単勝オッズを材料にする。馬体重がまだ無ければ予想モデルの誤り（``ValueError`` など）がそのまま出る。"""

    def __init__(self, models: Path = DEFAULT_MODELS, command: PredictCommand | None = None) -> None:
        self._models = models
        self._command = command or PredictCommand()

    def of(self, con: duckdb.DuckDBPyConnection, rid: str, db_path: Path | None = None) -> pd.DataFrame:
        """列は ``horse_no``・``win_model``・``top3_model``・``win_free``・``top3_free``。"""
        race_day = self._predict(con, rid, db_path, PredictionTiming.RACE_DAY, {WIN_PROBABILITY: WIN_MODEL, PROBABILITY: TOP3_MODEL})
        free = self._predict(con, rid, db_path, PredictionTiming.THURSDAY, {WIN_PROBABILITY: WIN_FREE, PROBABILITY: TOP3_FREE})
        return race_day.merge(free, on=HORSE_NO, how="left")

    def _predict(self, con: duckdb.DuckDBPyConnection, rid: str, db_path: Path | None, timing: PredictionTiming,
                 names: dict[str, str]) -> pd.DataFrame:
        args = argparse.Namespace(rid=rid, date=None, venue=None, race=None, timing=timing, odds=None, models=self._models, db=db_path)
        prediction = self._command.prediction(con, args)
        missing = [column for column in names if column not in prediction.columns]
        if missing:
            raise LookupError(f"全頭の予想（{timing.label}）に列がありません: {'・'.join(missing)}（モデル: {self._models}）")
        frame = prediction[[_HORSE_NO, *names]].rename(columns={_HORSE_NO: HORSE_NO, **names})
        frame[HORSE_NO] = pd.to_numeric(frame[HORSE_NO], errors="coerce")
        return frame.dropna(subset=[HORSE_NO]).astype({HORSE_NO: int})
