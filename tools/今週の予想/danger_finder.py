"""1レースの危険な人気馬を、予想「人気馬が4着以下になるかを予想」で判定する。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.favorites_out_of_top3.danger import BASE_OUT, DANGER, IS_DANGER, DangerJudge
from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND, dataset_builder
from yosou.favorites_out_of_top3.repository import DangerThresholdRepository
from yosou.favorites_out_of_top3.workflow import PROBABILITY, SEGMENTS, TIMINGS, PredictionWorkflow
from yosou.shared.dataset import OddsResolver, PopularityApplier
from yosou.shared.dataset import column_names as ids
from yosou.shared.feature import PredictionTiming
from yosou.shared.repository import AnnouncedOddsRepository
from yosou.shared.workflow import SegmentedPrediction

from 今週の予想 import forecast_columns as columns

#: 「危険」を印（消）に使う人気帯。利用者の決定（2026-10-03）: 今の人気馬の予想は 2〜5番人気の線が 0.0〜0.02 ポイントで、
#: 2〜3番人気がほぼ全頭「危険」になるため、検証で確かめられている1番人気だけを使う。ほかの人気帯の危険度は参考に出すだけ。
MARKED_BANDS: tuple[str, ...] = ("1番人気",)


class DangerFinder:
    """1レースの人気馬（13頭以下は1〜3番人気、14頭以上は1〜5番人気）ごとに、4着以下になる確率・市場から見た4着以下の確率・
    危険度（その差）・人気帯の線・危険かを出す（設計書「買うレースと買い目を決める」07 の 3）。

    ``python -m yosou.favorites_out_of_top3 predict`` と同じ組み立て。人気の分からない木曜は判定しない（空の表）。
    ``models`` は学習済みのモデルと、人気帯ごとの線（``danger_thresholds.json``）の置き場所。
    戻り値の列は ``horse_id`` と ``forecast_columns`` の危険の列。行は人気馬だけ。``is_danger`` は ``MARKED_BANDS`` の人気帯だけで立てる
    （ほかの人気帯は、危険度が線以上でも立てない）。
    """

    def __init__(self, models: Path) -> None:
        self._models = Path(models)

    def find(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming) -> pd.DataFrame:
        if timing not in TIMINGS:
            return pd.DataFrame(columns=[columns.HORSE_ID, *columns.DANGER_COLUMNS])
        lines = DangerThresholdRepository(self._models).load().get(timing, {})
        repository = AnnouncedOddsRepository(con)
        workflow = PredictionWorkflow(
            dataset_builder(con), SegmentedPrediction(SEGMENTS, self._models), PopularityApplier(repository),
            OddsResolver(repository), {timing: DangerJudge(lines)},
        )
        predicted = workflow.run(race_id, timing)
        return pd.DataFrame({
            columns.HORSE_ID: predicted[ids.HORSE_ID].astype(str).to_numpy(),
            columns.FAVORITE_BAND: predicted[FAVORITE_BAND].astype(str).to_numpy(),
            columns.OUT_PROBABILITY: predicted[PROBABILITY].to_numpy(dtype=float),
            columns.MARKET_OUT: predicted[BASE_OUT].to_numpy(dtype=float),
            columns.DANGER_SCORE: predicted[DANGER].to_numpy(dtype=float),
            columns.DANGER_LINE: predicted[FAVORITE_BAND].map(lines).astype(float).to_numpy(),
            columns.IS_DANGER: ((predicted[IS_DANGER] != "") & predicted[FAVORITE_BAND].isin(MARKED_BANDS)).to_numpy(),
        })
