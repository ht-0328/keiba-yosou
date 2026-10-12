"""1日のレースごとに「荒れる」点数を出し、高い順に並べる。"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

import duckdb

from yosou.shared.betting import TicketType
from yosou.shared.feature import PredictionTiming
from yosou.upset_level.dataset import BetType, UpsetLevel
from yosou.upset_level.workflow import PredictionWorkflow
from yosou.upset_premise.selection import BigPayoutChance, RaceSelectionScore

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.race_forecaster import RaceForecaster
from 今週の予想.timing_chooser import TimingChooser
from 帯狙い.announced_combo_odds import AnnouncedComboOdds
from 帯狙い.forecast_horses import ForecastHorses

#: 荒れ具合の予想の券種と段。3連単の大荒れ（10万円以上）と超荒れ（50万円以上）の確率の合計 = 3連単が 1,000倍以上で決まる確率（設計書 15 の 1）。
SELECTION_BET = BetType.TRIFECTA
SELECTION_LEVELS: tuple[UpsetLevel, ...] = (UpsetLevel.BIG, UpsetLevel.HUGE)
#: 「荒れる」と決めて買う線（点数がこの値以上のレースを全部買う）。研究「百万馬券を当てる」の docs/06 で決めた既定。
DEFAULT_LINE = 0.40
#: 点数の種類（--score）。平均 = 荒れ具合の予想と予想が見た確率の平均（既定）。大荒れ＋超荒れ = 荒れ具合の予想だけ（レース数が多く、速い）。
SCORE_BLEND, SCORE_UPSET = "平均", "大荒れ＋超荒れ"
SCORE_CHOICES: tuple[str, ...] = (SCORE_BLEND, SCORE_UPSET)


@dataclass(frozen=True)
class RaceChance:
    """1レースの「荒れる」点数と、その元になった2つの確率、点数を出した時点、今の予想の結果。

    ``probability`` は点数（荒れ具合の確率と予想が見た確率の平均）。``chance`` と ``usual_forecast`` は、組ごとのオッズか
    今の予想が無いレースでは None（点数は荒れ具合の確率だけ）。
    """

    race_id: str
    timing: PredictionTiming
    probability: float
    upset_probability: float
    chance: float | None
    usual_forecast: dict[str, Any] | None


class ObiDayPicker:
    """1日のレース（``race_ids``）ごとに、DB の情報から時点を選び（``TimingChooser``）、「荒れる」点数を出して高い順に並べる。

    点数は、荒れ具合の予想（``yosou.upset_level``）の3連単が 1,000倍以上になる確率（大荒れ＋超荒れ）と、
    予想が見た 1,000倍以上になる確率（今の予想の全頭の1着の確率と、締め切り前の3連単のオッズから。``BigPayoutChance``）の平均
    （``RaceSelectionScore``）。線以上のレースが、その日に「荒れる」と決めて買うレース。
    今の予想は、今週の予想が保存した結果（``ForecastStore``。同じ時点のもの）があればそれを使い、無ければ ``forecaster`` で出す
    （1レース数十秒かかるので、先に今週の予想を動かしておくと速い）。
    ``score`` が「大荒れ＋超荒れ」なら、予想が見た確率を出さず、荒れ具合の予想の確率だけを点数にする（速い。選ぶレースは多くなる）。
    予測できないレース（障害・出馬表が足りない・オッズが全頭そろっていない など）は飛ばして、理由を標準エラーに出す。
    """

    def __init__(self, workflow: PredictionWorkflow, forecaster: RaceForecaster, store: ForecastStore,
                 score: str = SCORE_BLEND, chooser: TimingChooser | None = None) -> None:
        if score not in SCORE_CHOICES:
            raise ValueError(f"知らない点数です: {score}（{' / '.join(SCORE_CHOICES)}）")
        self._workflow = workflow
        self._forecaster = forecaster
        self._store = store
        self.score = score
        self._with_chance = score == SCORE_BLEND
        self._chooser = chooser or TimingChooser()

    def rank(self, con: duckdb.DuckDBPyConnection, race_ids: list[str]) -> list[RaceChance]:
        chances = [chance for chance in (self._one(con, race_id) for race_id in race_ids) if chance is not None]
        return sorted(chances, key=lambda chance: (-chance.probability, chance.race_id))

    @staticmethod
    def above(ranked: list[RaceChance], line: float) -> list[RaceChance]:
        """並べたレースのうち、点数が線以上のもの（買うレース）。"""
        return [chance for chance in ranked if chance.probability >= line]

    def _one(self, con: duckdb.DuckDBPyConnection, race_id: str) -> RaceChance | None:
        try:
            timing = self._chooser.choose(con, race_id).timing
            prediction = self._workflow.run(race_id, timing, bets=[SELECTION_BET])
            upset = sum(float(prediction[level.label].iloc[0]) for level in SELECTION_LEVELS)
        except (ValueError, LookupError, FileNotFoundError) as error:
            print(f"  {race_id}: 荒れ具合を出せません: {error}", file=sys.stderr, flush=True)
            return None
        if not self._with_chance:
            return RaceChance(race_id, timing, RaceSelectionScore().of(upset, None), upset, None, None)
        usual = self._usual_forecast(con, race_id, timing)
        chance = self._chance(con, race_id, usual)
        return RaceChance(race_id, timing, RaceSelectionScore().of(upset, chance), upset, chance, usual)

    def _usual_forecast(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming) -> dict[str, Any] | None:
        """今の予想の結果。保存してある同じ時点の結果があればそれ、無ければ出す。出せなければ None。"""
        saved = self._store.load(race_id)
        if saved is not None and saved.get("timing") == timing.label:
            return saved
        try:
            print(f"  {race_id}: 今の予想（{timing.label}）を出しています …", file=sys.stderr, flush=True)
            return self._forecaster.forecast(con, race_id, timing)
        except (ValueError, LookupError, FileNotFoundError) as error:
            print(f"  {race_id}: 今の予想を出せません: {error}", file=sys.stderr, flush=True)
            return None

    @staticmethod
    def _chance(con: duckdb.DuckDBPyConnection, race_id: str, usual: dict[str, Any] | None) -> float | None:
        """予想が見た 1,000倍以上になる確率。今の予想か、組ごとのオッズが無ければ None。"""
        if usual is None:
            return None
        odds = AnnouncedComboOdds(con).read(race_id, TicketType.TRIFECTA)
        if not odds:
            return None
        return BigPayoutChance().of(ForecastHorses().of(usual), odds)
