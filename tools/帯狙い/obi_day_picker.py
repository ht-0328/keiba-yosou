"""1日のレースごとに荒れやすさを出し、いちばん荒れそうなレースを選ぶ。"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import duckdb

from yosou.shared.feature import PredictionTiming
from yosou.upset_level.dataset import BetType, UpsetLevel
from yosou.upset_level.workflow import PredictionWorkflow

from 今週の予想.timing_chooser import TimingChooser

#: レースを選ぶ点数にする、荒れ具合の予想の券種と段（3連単の超荒れ = 50万円以上）。研究「百万馬券を当てる」の docs/04 の 1 で採用した。
SELECTION_BET, SELECTION_LEVEL = BetType.TRIFECTA, UpsetLevel.HUGE


@dataclass(frozen=True)
class RaceChance:
    """1レースの、レースを選ぶ点数（3連単の超荒れの確率）と、それを出した時点。"""

    race_id: str
    timing: PredictionTiming
    probability: float


class ObiDayPicker:
    """1日のレース（``race_ids``）ごとに、DB の情報から時点を選び（``TimingChooser``）、荒れ具合の予想（``yosou.upset_level``）で
    3連単の超荒れの確率を出して、高い順に並べる。先頭のレースが、その日に「荒れる」と決めて買うレース（1日1レース）。

    予測できないレース（障害・出馬表が足りない・オッズが全頭そろっていない など）は飛ばして、理由を標準エラーに出す。
    """

    def __init__(self, workflow: PredictionWorkflow, chooser: TimingChooser | None = None) -> None:
        self._workflow = workflow
        self._chooser = chooser or TimingChooser()

    def rank(self, con: duckdb.DuckDBPyConnection, race_ids: list[str]) -> list[RaceChance]:
        chances = [chance for chance in (self._one(con, race_id) for race_id in race_ids) if chance is not None]
        return sorted(chances, key=lambda chance: chance.probability, reverse=True)

    def _one(self, con: duckdb.DuckDBPyConnection, race_id: str) -> RaceChance | None:
        try:
            timing = self._chooser.choose(con, race_id).timing
            prediction = self._workflow.run(race_id, timing, bets=[SELECTION_BET])
            return RaceChance(race_id, timing, float(prediction[SELECTION_LEVEL.label].iloc[0]))
        except (ValueError, LookupError, FileNotFoundError) as error:
            print(f"  {race_id}: 荒れ具合を出せません: {error}", file=sys.stderr, flush=True)
            return None
