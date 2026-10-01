"""学習のあとに、時点ごと・区分ごとの「買い」の線を検証期間で決めて保存する。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from 共通.render import Table

from yosou.shared.command.cell_format import rounded
from yosou.shared.dataset import PeriodSplitter, TrainingData, TrainingPeriod
from yosou.shared.dataset.column_names import PLACE_PAYOUT
from yosou.shared.feature import PredictionTiming
from yosou.shared.place_value import PLACE_VALUE, PlaceExpectedValue, PlacePriceEstimator
from yosou.shared.repository import PlacePriceRepository
from yosou.shared.workflow import CalibrationCheck, ModelSegments, SegmentedHoldoutPrediction
from yosou.shared.workflow.calibration_check import PART, PART_VALID, SEGMENT, TIMING

from ..buy_line import HIT_RATE, LINE, MIN_POINTS, PAYBACK, POINTS, BuyLineChooser
from ..repository import BuyLineRepository


class BuyLineStep:
    """保存したモデルで検証データを予測して複勝の期待値を出し、時点ごと・区分ごとの「買い」の線（``BuyLineChooser``）を
    決めて、モデルの置き場所に保存する（設計書 16 の 3）。

    予測は確率のずれの確かめ（``CalibrationCheck``）と同じ流れで作り、検証期間の行だけを使う（テスト期間は使わない）。
    見込みの倍率（``place_price.json``）は、先に ``PlacePriceStep`` が保存したものを読む。無ければ線を決めない。
    返すのは、線の候補ごとの検証期間の成績の表と、決めた線の表。
    """

    def __init__(self, segments: ModelSegments, timings: Sequence[PredictionTiming]) -> None:
        self._segments = segments
        self._timings = tuple(timings)
        self._chooser = BuyLineChooser()

    def run(self, training_data: TrainingData, period: TrainingPeriod, models_root: Path) -> list[Table]:
        state = PlacePriceRepository(models_root).load()
        if state is None:
            return []
        valid = self._valid_values(training_data, period, models_root, state)
        groups = list(valid.groupby([TIMING, SEGMENT], sort=False))
        candidates = pd.concat([self._rates(key, group) for key, group in groups], ignore_index=True)
        lines = {key: self._chooser.choose(group[PLACE_VALUE], group[PLACE_PAYOUT]) for key, group in groups}
        path = BuyLineRepository(models_root).save(self._by_timing(lines))
        return [self._candidates_table(candidates), self._lines_table(lines, path)]

    def _valid_values(self, training_data: TrainingData, period: TrainingPeriod, models_root: Path,
                      state: dict) -> pd.DataFrame:
        """検証期間の、期待値の出る行（前日・当日）の時点・区分・複勝の期待値・複勝の払戻。"""
        split = PeriodSplitter(period).split(training_data)
        value = PlaceExpectedValue(PlacePriceEstimator.from_state(state))
        check = CalibrationCheck(self._segments, SegmentedHoldoutPrediction(self._segments, models_root), value,
                                 self._timings)
        frame = check.run(split)
        return frame[(frame[PART] == PART_VALID) & frame[PLACE_VALUE].notna()]

    def _rates(self, key: tuple[str, str], group: pd.DataFrame) -> pd.DataFrame:
        timing, zone = key
        return self._chooser.rates(group[PLACE_VALUE], group[PLACE_PAYOUT]).assign(**{TIMING: timing, SEGMENT: zone})

    def _by_timing(self, lines: dict[tuple[str, str], float]) -> dict[PredictionTiming, dict[str, float]]:
        """（時点の名前, 区分）→ 線 を、時点 → 区分 → 線 にする。"""
        grouped: dict[PredictionTiming, dict[str, float]] = {}
        for (timing, zone), line in lines.items():
            grouped.setdefault(PredictionTiming.parse(timing), {})[zone] = line
        return grouped

    def _candidates_table(self, candidates: pd.DataFrame) -> Table:
        rows = [[row[TIMING], row[SEGMENT], row[LINE], int(row[POINTS]), rounded(row[HIT_RATE]), rounded(row[PAYBACK])]
                for _, row in candidates.iterrows()]
        return Table([TIMING, SEGMENT, "複勝の期待値の線", "検証の点数", "検証の的中率", "検証の回収率"], rows,
                     title="「買い」の線の候補ごとの成績（検証データ）",
                     note="線以上の穴馬の複勝を全部 100円ずつ買ったときの成績。確定オッズで見積もるので、実際に買う時点より楽観側。")

    def _lines_table(self, lines: dict[tuple[str, str], float], path: Path) -> Table:
        rows = [[timing, zone, line] for (timing, zone), line in lines.items()]
        return Table([TIMING, SEGMENT, "複勝の期待値の線"], rows, title="「買い」の線（検証データで決めた値）",
                     note=f"保存した場所: {path}。決まりは、検証データで回収率が 100% を超え、{MIN_POINTS}点以上残る線のうち、"
                          "回収率がいちばん高い線。空欄は線を決められなかった区分（その区分には「買い」を付けない）。")
