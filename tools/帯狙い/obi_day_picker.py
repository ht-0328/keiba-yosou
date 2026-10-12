"""1日のレースごとに「3連単が 1,000倍以上になる確率」を出し、高い順に並べる。"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import duckdb

from yosou.shared.feature import PredictionTiming
from yosou.upset_level.dataset import BetType, UpsetLevel
from yosou.upset_level.workflow import PredictionWorkflow

from 今週の予想.timing_chooser import TimingChooser

#: レースを選ぶ点数にする、荒れ具合の予想の券種と段。3連単の大荒れ（10万円以上）と超荒れ（50万円以上）の確率の合計 =
#: 3連単が 1,000倍以上で決まる確率（設計書 15 の 1）。
SELECTION_BET = BetType.TRIFECTA
SELECTION_LEVELS: tuple[UpsetLevel, ...] = (UpsetLevel.BIG, UpsetLevel.HUGE)
#: 「荒れる」と決めて買う線（この確率以上のレースを全部買う）。研究「百万馬券を当てる」の docs/06 で決めた既定。
DEFAULT_LINE = 0.40


@dataclass(frozen=True)
class RaceChance:
    """1レースの、レースを選ぶ点数（3連単が 1,000倍以上になる確率）と、それを出した時点。"""

    race_id: str
    timing: PredictionTiming
    probability: float


class ObiDayPicker:
    """1日のレース（``race_ids``）ごとに、DB の情報から時点を選び（``TimingChooser``）、荒れ具合の予想（``yosou.upset_level``）で
    3連単が 1,000倍以上になる確率（大荒れ＋超荒れ）を出して、高い順に並べる。線以上のレースが、その日に「荒れる」と決めて買うレース。

    予測できないレース（障害・出馬表が足りない・オッズが全頭そろっていない など）は飛ばして、理由を標準エラーに出す。
    """

    def __init__(self, workflow: PredictionWorkflow, chooser: TimingChooser | None = None) -> None:
        self._workflow = workflow
        self._chooser = chooser or TimingChooser()

    def rank(self, con: duckdb.DuckDBPyConnection, race_ids: list[str]) -> list[RaceChance]:
        chances = [chance for chance in (self._one(con, race_id) for race_id in race_ids) if chance is not None]
        return sorted(chances, key=lambda chance: (-chance.probability, chance.race_id))

    @staticmethod
    def above(ranked: list[RaceChance], line: float) -> list[RaceChance]:
        """並べたレースのうち、確率が線以上のもの（買うレース）。"""
        return [chance for chance in ranked if chance.probability >= line]

    def _one(self, con: duckdb.DuckDBPyConnection, race_id: str) -> RaceChance | None:
        try:
            timing = self._chooser.choose(con, race_id).timing
            prediction = self._workflow.run(race_id, timing, bets=[SELECTION_BET])
            probability = sum(float(prediction[level.label].iloc[0]) for level in SELECTION_LEVELS)
            return RaceChance(race_id, timing, probability)
        except (ValueError, LookupError, FileNotFoundError) as error:
            print(f"  {race_id}: 荒れ具合を出せません: {error}", file=sys.stderr, flush=True)
            return None
