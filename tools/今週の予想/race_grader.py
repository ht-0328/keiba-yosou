"""1レースの的中率・配当率と等級をまとめる。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from yosou.shared.feature import PredictionTiming
from yosou.shared.race_grade import GradeScale

from 今週の予想 import forecast_columns as columns
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.payout_rate import PayoutRate
from 今週の予想.race_grades import RaceGrades


class RaceGrader:
    """1レースの的中率（◎ が3着以内に来る確率）と配当率（``PayoutRate``）を出し、``GradeScale`` で S・A・B・C にする
    （設計書「買うレースと買い目を決める」の 03 の 5）。

    的中率は全頭の結果（``RaceForecaster._horses`` の辞書の並び）の ◎ の ``probability``（3着以内のモデルの確率。2つのモデルの平均）。
    ◎ がいなければ None。配当率は荒れ具合の予想から出し、出せなければ None（等級も None）。
    ``upset_models`` は荒れ具合の予想の学習済みモデルの置き場所。
    """

    def __init__(self, upset_models: Path) -> None:
        self._payout = PayoutRate(upset_models)
        self._scale = GradeScale()

    def grade(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming, horses: list[dict[str, Any]]) -> RaceGrades:
        hit = self._hit_rate(horses)
        payout = self._payout.of(con, race_id, timing)
        return RaceGrades(hit, self._scale.of(hit), payout, self._scale.of(payout))

    @staticmethod
    def _hit_rate(horses: list[dict[str, Any]]) -> float | None:
        tops = [horse for horse in horses if horse.get(columns.MARK) == TOP_MARK]
        value = tops[0].get(columns.PROBABILITY) if tops else None
        return None if value is None else float(value)
