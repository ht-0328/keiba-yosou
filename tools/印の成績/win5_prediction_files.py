"""当日と前日の区切りごとの1着の予測のファイルを読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 印の成績.prediction_file import TEST, PredictionFile
from 印の成績.win5_fold_predictions import Win5FoldPredictions

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: 既定の予測（研究「複勝以外の回収率100超」が作った、今のモデルと同じ作りの区切りごとの予測。設計書「近走と適性からWIN5の買い目を決める」16 の 1.）。
_PREDICTIONS = _PROJECT_ROOT / "reports" / "複勝以外の回収率100超"
DEFAULT_RACE_DAY = _PREDICTIONS / "predictions-2015から" / "dscore_finish_race_day" / "win-race_day.pkl"
DEFAULT_DAY_BEFORE = _PREDICTIONS / "predictions-2019から" / "dscore_day_before" / "win-day_before.pkl"
#: 読む列。
_COLUMNS = ["race_id", "race_date", "horse_no", "probability", "fold"]


class Win5PredictionFiles:
    """当日と前日の1着の予測（研究「既存モデルの改善」の ``walk_forward.py`` と同じ形の pkl）を読み、テスト期間の行だけにする。

    区切りのテスト期間は、前日と当日の両方の予測がある区切りだけを残す（WIN5 の後ろのほうのレースは前日の確率を使うため）。
    """

    def __init__(self, race_day: Path | str = DEFAULT_RACE_DAY, day_before: Path | str = DEFAULT_DAY_BEFORE) -> None:
        self._race_day = PredictionFile(str(race_day))
        self._day_before = PredictionFile(str(day_before))

    @property
    def names(self) -> tuple[str, str]:
        """当日・前日の予測のファイルのパス（結果の条件に書く）。"""
        return str(self._race_day.path), str(self._day_before.path)

    def load(self) -> Win5FoldPredictions:
        race_day, day_before = self._tested(self._race_day), self._tested(self._day_before)
        folds = self._folds(race_day).merge(self._folds(day_before)[["fold"]], on="fold")
        return Win5FoldPredictions(race_day, day_before, folds.sort_values("start").reset_index(drop=True))

    def _tested(self, file: PredictionFile) -> pd.DataFrame:
        table = file.load()
        tested = table.loc[table["period"] == TEST, _COLUMNS].copy()
        if tested.empty:
            raise LookupError(f"テスト期間の行がありません: {file.path}")
        tested["race_date"] = pd.to_datetime(tested["race_date"]).dt.strftime("%Y-%m-%d")
        tested["horse_no"] = tested["horse_no"].astype(int)
        return tested.reset_index(drop=True)

    def _folds(self, tested: pd.DataFrame) -> pd.DataFrame:
        """区切りごとのテスト期間の始まりと終わり。"""
        spans = tested.groupby("fold")["race_date"].agg(["min", "max"]).reset_index()
        return spans.rename(columns={"min": "start", "max": "end"})
