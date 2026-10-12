"""第1段: レースごとに、レースの選び方（モデル・比べる目安・条件のルール）の点数を並べる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_ID
from yosou.shared.feature import PredictionTiming

from 既存モデルの改善.analysis.walk_forward import PredictionStore
from 既存モデルの改善.analysis.walk_forward.prediction_frame import PART, PART_TEST, PREDICTION_COLUMN, WINDOW
from 既存モデルの改善.analysis.walk_forward.upset_window_trainer import BET

from .crowded_split_rule import crowded_split_score

#: 予測の置き場所の名前（walk.py と同じ）。
RACE_OBI = "race_obi"
RACE_BIG = "race_big"
UPSET_BASELINE = ("upset_level", "current")
#: 比べる目安に使う、荒れ具合の予想の券種と段。1,000倍以上の目安は、大荒れと超荒れの確率の合計。
BASELINE_BET, BASELINE_LEVEL = "3連単", "超荒れ"
BIG_LEVELS: tuple[str, ...] = ("大荒れ", "超荒れ")
#: 点数の列の名前。
RULE = "条件のルール（多頭数で人気が割れている）"
BASELINE = "比べる目安（荒れ具合の予想の3連単の超荒れの確率）"
BIG_BASELINE = "荒れ具合の予想の3連単の大荒れ＋超荒れの確率"


def model_column(timing: PredictionTiming) -> str:
    """帯になる確率のモデルの点数の列の名前。"""
    return f"帯になる確率のモデル（{timing.label}）"


def big_model_column(timing: PredictionTiming) -> str:
    """1,000倍以上になる確率の専用モデルの点数の列の名前。"""
    return f"1,000倍以上になる確率のモデル（{timing.label}）"


class RaceSelectionScores:
    """レースごとの事例の表（``race_frame`` の結果）に、テスト期間の予測から、選び方ごとの点数の列を足す。

    予測が無いレース（テスト期間の外）は落とす。区切りの名前の列も足す。
    """

    def __init__(self, store: PredictionStore) -> None:
        self._store = store

    def scores(self, races: pd.DataFrame) -> pd.DataFrame:
        model = {model_column(timing): self._model(RACE_OBI, timing) for timing in PredictionTiming
                 if self._store.exists(RACE_OBI, timing.value)}
        model |= {big_model_column(timing): self._model(RACE_BIG, timing) for timing in PredictionTiming
                  if self._store.exists(RACE_BIG, timing.value)}
        tested = races.merge(self._windows(), on=RACE_ID, how="inner")
        for column, values in model.items():
            tested[column] = tested[RACE_ID].map(values)
        baseline = self._baseline()
        tested[BASELINE] = tested[RACE_ID].map(baseline[BASELINE_LEVEL]) if not baseline.empty else float("nan")
        tested[BIG_BASELINE] = tested[RACE_ID].map(baseline[list(BIG_LEVELS)].sum(axis=1)) if not baseline.empty else float("nan")
        tested[RULE] = crowded_split_score(tested)
        return tested

    def _test(self, model: str, key: str) -> pd.DataFrame:
        predictions = self._store.read(model, key)
        return predictions[predictions[PART].eq(PART_TEST)]

    def _windows(self) -> pd.DataFrame:
        test = self._test(RACE_OBI, PredictionTiming.RACE_DAY.value)
        return test[[RACE_ID, WINDOW]].drop_duplicates(RACE_ID)

    def _model(self, model: str, timing: PredictionTiming) -> pd.Series:
        test = self._test(model, timing.value)
        return test.set_index(RACE_ID)[PREDICTION_COLUMN]

    def _baseline(self) -> pd.DataFrame:
        """荒れ具合の予想の3連単の、レースごとの4段階の確率（無ければ空）。"""
        if not self._store.exists(*UPSET_BASELINE):
            return pd.DataFrame()
        test = self._test(*UPSET_BASELINE)
        return test[test[BET].eq(BASELINE_BET)].set_index(RACE_ID)
