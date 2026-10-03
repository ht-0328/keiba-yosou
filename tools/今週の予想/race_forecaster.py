"""1レースを予想して、全頭の順位・印・理由をまとめる。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from 共通 import card

from yosou.form_aptitude_top3.command.development_root_argument import DEFAULT_DEVELOPMENT_ROOT
from yosou.form_aptitude_top3.dataset import OddsResolver, ability_dataset_builder, race_day_dataset_builder
from yosou.form_aptitude_top3.feature import WIN_ODDS
from yosou.form_aptitude_top3.workflow import (
    ABILITY_TIMINGS,
    PACE_TIMINGS,
    POOL_FREE_FOLDER,
    PROBABILITY,
    WIN_FOLDER,
    WIN_PROBABILITY,
    ExplainedPrediction,
    PredictionWorkflow,
)
from yosou.race_development.workflow import DevelopmentPaceWorkflow
from yosou.shared.dataset import column_names as ids
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP3_RATE
from yosou.shared.place_value import PLACE_VALUE, PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, PlacePriceRepository
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER as FIGURE_CACHE
from yosou.shared.win_value import WIN_VALUE, ExpectationLevel
from yosou.shared.workflow import ModelSegments, SegmentedPrediction

from 今週の予想 import forecast_columns as columns
from 今週の予想.danger_finder import DangerFinder
from 今週の予想.horse_evaluator import HorseEvaluator
from 今週の予想.mark_rule import MarkRule
from 今週の予想.timing_chooser import TimingChooser

#: 予想の結果の表の列 → この道具の列。
_RENAMES: dict[str, str] = {
    ids.HORSE_ID: columns.HORSE_ID, ids.HORSE_NO: columns.HORSE_NO, ids.HORSE_NAME: columns.HORSE_NAME,
    PROBABILITY: columns.PROBABILITY, WIN_ODDS: columns.WIN_ODDS, TOP3_RATE: columns.MARKET_TOP3, PLACE_VALUE: columns.PLACE_VALUE,
    WIN_PROBABILITY: columns.WIN_PROBABILITY, WIN_VALUE: columns.WIN_VALUE,
}
#: 1頭の結果に入れる、表の列。
_HORSE_COLUMNS: tuple[str, ...] = (
    columns.RANK, columns.MARK, columns.MARK_REASON, columns.HORSE_NO, columns.HORSE_NAME, columns.HORSE_ID,
    columns.PROBABILITY, columns.WIN_ODDS, columns.POPULARITY, columns.MARKET_TOP3, columns.PLACE_VALUE, columns.UPDOWN,
    columns.WIN_PROBABILITY, columns.WIN_VALUE, *columns.DANGER_COLUMNS,
)
#: 予想の名前（画面に出す）。
MODEL_NAME = "近走と適性から3着以内を予想（3着以内と1着のモデル。危険な人気馬は 人気馬が4着以下になるかを予想）"
#: 結果の作り方の版。印の決め方や理由の作り方を変えたら上げる（``forecast.py --skip-saved`` は、版の違う結果を作り直す）。
FORECAST_VERSION = 4


class RaceForecaster:
    """1レースを、予想「近走と適性から3着以内を予想」の学習済みモデルで予想し、全頭の順位・印・良い点と悪い点・総合をまとめる。

    時点は ``TimingChooser`` が DB の情報から選ぶ（``timing`` を渡せばその時点）。組み立ては
    ``python -m yosou.form_aptitude_top3 predict`` と同じ（木曜は展開の予想の結果も使う。当日に券種のオッズが無ければ券種オッズなしのモデル。
    3着以内のモデルと1着のモデルの両方で予測する）。
    前日・当日は、危険な1番人気を予想「人気馬が4着以下になるかを予想」で判定して、印を付ける前に消にする（``DangerFinder``）。
    ◎ は単勝 30倍以下の馬の中で単勝の期待値（1着になる確率 × 単勝オッズ）が1位の馬で、レースの期待度（◎ の期待値が 1.00 以上なら高）も出す
    （設計書「近走と適性から3着以内を予想」の 16 の 6。木曜は期待値が無いので期待度も無い）。
    ``models`` は学習済みのモデルの置き場所、``favorite_models`` は人気馬の予想の学習済みモデルの置き場所。結果は JSON にできる辞書。
    """

    def __init__(self, models: Path, favorite_models: Path, figure_cache: Path = FIGURE_CACHE,
                 development_root: Path = DEFAULT_DEVELOPMENT_ROOT) -> None:
        self._models = Path(models)
        self._dangers = DangerFinder(favorite_models)
        self._figure_cache = Path(figure_cache)
        self._development_root = Path(development_root)
        self._chooser = TimingChooser()
        self._marks = MarkRule()
        self._evaluator = HorseEvaluator()
        self._expectation = ExpectationLevel()

    def forecast(self, con: duckdb.DuckDBPyConnection, race_id: str,
                 timing: PredictionTiming | None = None) -> dict[str, Any]:
        header = card.race_header(con, race_id)
        if header["コース"].startswith("障害"):
            raise ValueError("障害レースは予想の対象外です（モデルは平地のレースで学んでいる）")
        choice = self._chooser.choose(con, race_id)
        chosen = timing or choice.timing
        reason = choice.reason if timing is None else f"{chosen.label}のモデル（指定）"
        explained = self._workflow(con, chosen).explain(race_id, chosen)
        horses = self._horses(explained, self._dangers.find(con, race_id, chosen))
        return {
            "version": FORECAST_VERSION, "rid": race_id, "title": card.header_title(header), "header": header, "model": MODEL_NAME,
            "timing": chosen.label, "timing_reason": reason, "pool_free": explained.pool_free,
            "expectation": self._race_expectation(horses),
            "made_at": datetime.now().isoformat(timespec="seconds"), "horses": horses,
        }

    def _race_expectation(self, horses: list[dict[str, Any]]) -> str | None:
        """レースの期待度（高・低）。◎ の単勝の期待値から決める。期待値が無ければ（木曜・1着のモデルが無い）None。"""
        tops = [horse for horse in horses if horse[columns.MARK] == "◎"]
        return self._expectation.of(tops[0].get(columns.WIN_VALUE)) if tops else None

    def _horses(self, explained: ExplainedPrediction, dangers: pd.DataFrame) -> list[dict[str, Any]]:
        """全頭の結果（3着以内の確率の高い順）。``dangers`` は人気馬の危険の判定（``DangerFinder``。木曜は空）。"""
        table = explained.table.rename(columns=_RENAMES)
        table = table[[column for column in _RENAMES.values() if column in table.columns]]
        table = table.assign(**{"_row": table.index, columns.HORSE_ID: table[columns.HORSE_ID].astype(str)})
        dangers = dangers.assign(**{columns.HORSE_ID: dangers[columns.HORSE_ID].astype(str)})
        table = table.merge(dangers, on=columns.HORSE_ID, how="left").set_index(table.index)
        marked = self._marks.assign(table)
        horses = []
        for _, horse in marked.iterrows():
            row = horse["_row"]
            evaluation = self._evaluator.evaluate(horse, explained.features.loc[row], explained.contributions.loc[row])
            horses.append({**{column: _plain(horse.get(column)) for column in _HORSE_COLUMNS}, **evaluation})
        return horses

    def _workflow(self, con: duckdb.DuckDBPyConnection, timing: PredictionTiming) -> PredictionWorkflow:
        """その時点の予測の流れ（``PredictCommand`` と同じ組み立て）。"""
        builder = (ability_dataset_builder(con, self._figure_cache) if timing in ABILITY_TIMINGS
                   else race_day_dataset_builder(con, self._figure_cache))
        pace = None
        if timing in PACE_TIMINGS:
            development = DevelopmentPaceWorkflow(self._development_root / "models")
            pace = lambda race_id, at, given: development.run(con, race_id, at, given)  # noqa: E731
        return PredictionWorkflow(
            builder, SegmentedPrediction(ModelSegments(), self._models),
            OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(self._place_price()),
            pool_free=SegmentedPrediction(ModelSegments(), self._models / POOL_FREE_FOLDER), pace=pace,
            win_predictor=SegmentedPrediction(ModelSegments(), self._models / WIN_FOLDER),
            win_pool_free=SegmentedPrediction(ModelSegments(), self._models / POOL_FREE_FOLDER / WIN_FOLDER),
        )

    def _place_price(self) -> PlacePriceEstimator | None:
        state = PlacePriceRepository(self._models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None


def _plain(value: Any) -> Any:
    """numpy の数を Python の数にし、欠損値は None にする（JSON のため）。"""
    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and pd.isna(value):
        return None
    return value
