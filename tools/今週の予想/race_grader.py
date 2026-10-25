"""1レースの ◎ランク・的中率・配当率と等級をまとめる。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from yosou.shared.feature import PredictionTiming
from yosou.shared.race_grade import GradeScale, TopRankScale

from 今週の予想 import forecast_columns as columns
from 今週の予想.mark_rule import TOP_MARK
from 今週の予想.payout_rate import PayoutRate
from 今週の予想.race_grades import RaceGrades


class RaceGrader:
    """1レースの ◎ランク（◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数を ``TopRankScale`` で S・A・B・C に）・的中率（◎ の1着の確率）・
    配当率（``PayoutRate`` を ``GradeScale`` で S・A・B・C に）を出す（設計書「買うレースと買い目を決める」の 03 の 5）。

    材料は全頭の結果（``RaceForecaster._horses`` の辞書の並び）の ◎ の ``win_probability``（1着のモデルの確率。2つのモデルの平均）と
    ``win_value``（単勝の期待値）。◎ がいないか 1着のモデルが無ければ的中率は None、期待値が無ければ（木曜）◎ランクは None。
    配当率は荒れ具合の予想から出し、出せなければ None（等級も None）。``upset_models`` は荒れ具合の予想の学習済みモデルの置き場所。
    """

    def __init__(self, upset_models: Path) -> None:
        self._payout = PayoutRate(upset_models)
        self._rank = TopRankScale()
        self._scale = GradeScale()

    def grade(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming, horses: list[dict[str, Any]]) -> RaceGrades:
        top = next((horse for horse in horses if horse.get(columns.MARK) == TOP_MARK), None)
        hit = _number(top.get(columns.WIN_PROBABILITY)) if top is not None else None
        score = TopRankScale.score(hit, _number(top.get(columns.WIN_VALUE))) if top is not None else None
        payout = self._payout.of(con, race_id, timing)
        return RaceGrades(score, self._rank.of(score), hit, payout, self._scale.of(payout))


def _number(value: Any) -> float | None:
    return None if value is None else float(value)
