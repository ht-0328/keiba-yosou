"""1レースを予想して、全頭の順位・印・理由をまとめる。"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from 共通 import card

from yosou.form_aptitude_top3.command.development_root_argument import DEFAULT_DEVELOPMENT_ROOT
from yosou.form_aptitude_top3.dataset import OddsResolver, ability_dataset_builder, race_day_dataset_builder
from yosou.form_aptitude_top3.feature import WIN_ODDS
from yosou.form_aptitude_top3.workflow import (
    ABILITY_SCORE_TOP3_TIMINGS,
    ABILITY_SCORE_WIN_TIMINGS,
    ABILITY_TIMINGS,
    PACE_TIMINGS,
    POOL_FREE_FOLDER,
    PROBABILITY,
    SCORE_TIMINGS,
    SCORE_TOP3_TIMINGS,
    SCORE_WIN_TIMINGS,
    TRACK_BIAS_TIMINGS,
    TRACK_BIAS_TOP3_TIMINGS,
    TRACK_BIAS_WIN_TIMINGS,
    WEIGHT_DISCOUNT_TIMINGS,
    WEIGHT_DISCOUNT_TOP3_TIMINGS,
    WEIGHT_DISCOUNT_WIN_TIMINGS,
    WIN_FOLDER,
    WIN_PROBABILITY,
    ExplainedPrediction,
    PredictionWorkflow,
)
from yosou.ability_score import RaceAbilityScoreAttacher
from yosou.development_score import AdvantageTableStore, RaceScoreAttacher, cache_folder_beside
from yosou.development_score import names as score_names
from yosou.track_bias import MemoizedPaceForecast, PriorSlopeTableStore, RaceBiasAttacher, bias_cache_folder_beside
from yosou.weight_table import RaceWeightDiscountAttacher, WeightTableStore, weight_cache_folder_beside
from yosou.race_development.workflow import DevelopmentPaceWorkflow
from yosou.review import ReviewStore
from yosou.shared.dataset import column_names as ids
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP3_RATE, WIN_RATE, MarketPlaces
from yosou.shared.place_value import PLACE_VALUE, PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, BracketBlendWeightsRepository, ComboBlendWeightsRepository, PlacePriceRepository
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER as FIGURE_CACHE
from yosou.shared.win_value import WIN_VALUE, WinValueBand
from yosou.shared.workflow import ModelSegments, SegmentedPrediction
from yosou.shared.workflow.prediction_workflow import WIN_VALUE_MEMBER

from 今週の予想 import forecast_columns as columns
from 今週の予想.danger_finder import DangerFinder
from 今週の予想.danger_reasons import DangerReasons
from 今週の予想.forecast_tickets import ForecastTickets
from 今週の予想.forecast_version import FORECAST_VERSION
from 今週の予想.horse_evaluator import HorseEvaluator
from 今週の予想.filter_columns import MEMBER_SOURCES, member_column
from 今週の予想.mark_rule import OUT_MARK as DANGER_MARK
from 今週の予想.mark_rule import MarkRule
from 今週の予想.model_folders import DEFAULT_UPSET_MODELS
from 今週の予想.race_grader import RaceGrader
from 今週の予想.story_attacher import StoryAttacher
from 今週の予想.timing_chooser import TimingChooser

#: 予想の結果の表の列 → この道具の列。
_RENAMES: dict[str, str] = {
    ids.HORSE_ID: columns.HORSE_ID, ids.HORSE_NO: columns.HORSE_NO, ids.HORSE_NAME: columns.HORSE_NAME,
    PROBABILITY: columns.PROBABILITY, WIN_ODDS: columns.WIN_ODDS, TOP3_RATE: columns.MARKET_TOP3, PLACE_VALUE: columns.PLACE_VALUE,
    WIN_PROBABILITY: columns.WIN_PROBABILITY, WIN_VALUE: columns.WIN_VALUE, ids.PLACE_ODDS_LOW: columns.PLACE_ODDS_LOW,
    **{WIN_VALUE_MEMBER.format(member=source): member_column(columns.WIN_VALUE, member) for source, member in MEMBER_SOURCES.items()},
}
#: 1頭の結果に入れる、表の列。
_HORSE_COLUMNS: tuple[str, ...] = (
    columns.RANK, columns.MARK, columns.MARK_REASON, columns.HORSE_NO, columns.HORSE_NAME, columns.HORSE_ID,
    columns.PROBABILITY, columns.WIN_ODDS, columns.POPULARITY, columns.MARKET_TOP3, columns.PLACE_VALUE, columns.UPDOWN,
    columns.WIN_PROBABILITY, columns.WIN_VALUE, columns.MARKET_WIN, columns.AXIS, *columns.DANGER_COLUMNS,
)
#: 予想の名前（画面に出す）。
MODEL_NAME = "近走と適性から3着以内を予想（3着以内と1着のモデル。危険な人気馬は 人気馬が4着以下になるかを予想）"


class RaceForecaster:
    """1レースを、予想「近走と適性から3着以内を予想」の学習済みモデルで予想し、全頭の順位・印・良い点と悪い点・総合をまとめる。

    時点は ``TimingChooser`` が DB の情報から選ぶ（``timing`` を渡せばその時点）。組み立ては
    ``python -m yosou.form_aptitude_top3 predict`` と同じ（木曜は展開の予想の結果、前日は展開スコアも使う。当日に券種のオッズが無ければ券種オッズなしのモデル。
    3着以内のモデルと1着のモデルの両方で予測する）。
    前日・当日は、危険な人気馬（1レース1頭まで）を予想「人気馬が4着以下になるかを予想」で判定して、印を付ける前に消にする（``DangerFinder``）。
    ◎ は単勝 30倍以下の馬の中で単勝の期待値（1着になる確率 × 単勝オッズ）が1位の馬で、◎ の単勝の期待値が線（1.00）以上か未満か（``win_value_band``。
    買い方の決まりの条件。設計書「近走と適性から3着以内を予想」の 16 の 6。木曜は期待値が無いので無い）も出す。
    レースの目安として、◎ランク（◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数の S・A・B・C）・的中率（◎ の単勝が当たる確率）・配当率（配当が中荒れ以上になる確率。
    荒れ具合の予想 ``upset_models``。S・A・B・C）を出す（``RaceGrader``。設計書「買うレースと買い目を決める」の 03 の 5）。
    印から、設計書「買うレースと買い目を決める」08 の 2 の買い目（全券種）を組み、締め切り前のオッズで組の確率とトリガミを付ける（``ForecastTickets``。
    結果の ``tickets``。木曜はオッズが無いので期待値とトリガミは付かない）。
    各馬には近走の文（``StoryAttacher``。近5走の文・負けた走の敗因の候補・評価のことば。回顧の不利は ``review_store`` から）も付ける。
    ``models`` は学習済みのモデルの置き場所、``favorite_models`` は人気馬の予想の学習済みモデルの置き場所、``upset_models`` は荒れ具合の予想の
    学習済みモデルの置き場所。結果は JSON にできる辞書。
    """

    def __init__(self, models: Path, favorite_models: Path, figure_cache: Path = FIGURE_CACHE,
                 development_root: Path = DEFAULT_DEVELOPMENT_ROOT, review_store: ReviewStore | None = None,
                 upset_models: Path = DEFAULT_UPSET_MODELS) -> None:
        self._models = Path(models)
        self._dangers = DangerFinder(favorite_models)
        self._figure_cache = Path(figure_cache)
        self._development_root = Path(development_root)
        self._chooser = TimingChooser()
        self._marks = MarkRule()
        self._evaluator = HorseEvaluator()
        self._band = WinValueBand()
        self._grader = RaceGrader(upset_models)
        self._tickets = ForecastTickets(ComboBlendWeightsRepository(self._models).load(), BracketBlendWeightsRepository(self._models).load())
        self._danger_reasons = DangerReasons()
        self._stories = StoryAttacher(review_store)
        self._score_attacher: RaceScoreAttacher | None = None

    def forecast(self, con: duckdb.DuckDBPyConnection, race_id: str,
                 timing: PredictionTiming | None = None) -> dict[str, Any]:
        header = card.race_header(con, race_id)
        if header["コース"].startswith("障害"):
            raise ValueError("障害レースは予想の対象外です（モデルは平地のレースで学んでいる）")
        choice = self._chooser.choose(con, race_id)
        chosen = timing or choice.timing
        reason = choice.reason if timing is None else f"{chosen.label}のモデル（指定）"
        explained = self._workflow(con, chosen).explain(race_id, chosen)
        horses, marked = self._horses(explained, self._dangers.find(con, race_id, chosen))
        self._stories.attach(con, horses, date.fromisoformat(header["日付"]))
        band = self._win_value_band(horses)
        grades = self._grader.grade(con, race_id, chosen, horses)
        odds_known = chosen is not PredictionTiming.THURSDAY
        return {
            "version": FORECAST_VERSION, "rid": race_id, "title": card.header_title(header), "header": header, "model": MODEL_NAME,
            "timing": chosen.label, "timing_reason": reason, "pool_free": explained.pool_free,
            columns.WIN_VALUE_BAND: band, **grades.as_dict(), "odds_known": odds_known,
            "made_at": datetime.now().isoformat(timespec="seconds"), "horses": horses,
            "tickets": self._tickets.build(con, race_id, marked, band, odds_known, chosen is PredictionTiming.RACE_DAY),
            "pace": self._pace(race_id),
        }

    def _pace(self, race_id: str) -> dict[str, float] | None:
        """予想のペースの確率（展開スコアを足した時点だけ。回顧の表2「予想のペース」に残す）。無ければ None。"""
        scores = self._score_attacher.last_scores(race_id) if self._score_attacher is not None else None
        if scores is None or scores.empty:
            return None
        first = scores.iloc[0]
        return {"high": _plain(first.get(score_names.HIGH)), "even": _plain(first.get(score_names.EVEN)), "slow": _plain(first.get(score_names.SLOW))}

    def _win_value_band(self, horses: list[dict[str, Any]]) -> str | None:
        """◎ の単勝の期待値が線（1.00）以上か未満か。期待値が無ければ（木曜・1着のモデルが無い）None。"""
        tops = [horse for horse in horses if horse[columns.MARK] == "◎"]
        return self._band.of(tops[0].get(columns.WIN_VALUE)) if tops else None

    def _horses(self, explained: ExplainedPrediction, dangers: pd.DataFrame) -> tuple[list[dict[str, Any]], pd.DataFrame]:
        """全頭の結果（3着以内の確率の高い順）と、印を付けた表（買い目を組むのに使う）。``dangers`` は人気馬の危険の判定（``DangerFinder``。木曜は空）。"""
        table = explained.table.rename(columns=_RENAMES)
        table = table[[column for column in _RENAMES.values() if column in table.columns]]
        table = table.assign(**{"_row": table.index, columns.HORSE_ID: table[columns.HORSE_ID].astype(str)})
        if columns.WIN_ODDS in table.columns:
            table[columns.MARKET_WIN] = self._market_win(table[columns.WIN_ODDS])
        dangers = dangers.assign(**{columns.HORSE_ID: dangers[columns.HORSE_ID].astype(str)})
        table = table.merge(dangers, on=columns.HORSE_ID, how="left").set_index(table.index)
        marked = self._marks.assign(table)
        horses = []
        for index, horse in marked.iterrows():
            row = horse["_row"]
            if horse[columns.MARK] == DANGER_MARK:
                reasons = self._danger_reasons.of(explained.features.loc[row])
                if reasons:
                    marked.loc[index, columns.MARK_REASON] = horse[columns.MARK_REASON] + "。理由: " + "・".join(reasons)
                    horse = marked.loc[index]
            evaluation = self._evaluator.evaluate(horse, explained.features.loc[row], explained.contributions.loc[row])
            horses.append({**{column: _plain(horse.get(column)) for column in _HORSE_COLUMNS}, **evaluation})
        return horses, marked

    def _market_win(self, win_odds: pd.Series) -> pd.Series:
        """オッズから見た勝率（市場の見立て。組の期待値の「1着の比」の分母）。印の成績と同じ部品で出す。"""
        entries = pd.DataFrame({"race_id": "race", "win_odds": win_odds}, index=win_odds.index)
        return MarketPlaces().of(entries)[WIN_RATE]

    def _workflow(self, con: duckdb.DuckDBPyConnection, timing: PredictionTiming) -> PredictionWorkflow:
        """その時点の予測の流れ（``PredictCommand`` と同じ組み立て）。"""
        builder = (ability_dataset_builder(con, self._figure_cache) if timing in ABILITY_TIMINGS
                   else race_day_dataset_builder(con, self._figure_cache))
        pace = None
        if timing in PACE_TIMINGS:
            development = DevelopmentPaceWorkflow(self._development_root / "models")
            pace = lambda race_id, at, given: development.run(con, race_id, at, given)  # noqa: E731
        extras, win_extras = [], []
        self._score_attacher = None
        if timing in SCORE_TIMINGS:
            table = AdvantageTableStore(cache_folder_beside(self._development_root)).load(con)
            attacher = RaceScoreAttacher(con, self._development_root / "models", table)
            self._score_attacher = attacher
            extras = [attacher.attach] if timing in SCORE_TOP3_TIMINGS else []
            win_extras = [attacher.attach] if timing in SCORE_WIN_TIMINGS else []
        if timing in ABILITY_SCORE_TOP3_TIMINGS:
            extras.append(RaceAbilityScoreAttacher().attach)
        if timing in ABILITY_SCORE_WIN_TIMINGS:
            win_extras.append(RaceAbilityScoreAttacher().attach)
        if timing in TRACK_BIAS_TIMINGS:
            slopes, prior = PriorSlopeTableStore(bias_cache_folder_beside(self._development_root)).load(con)
            bias = RaceBiasAttacher(con, MemoizedPaceForecast(self._development_root / "models").run, slopes, prior)
            extras += [bias.attach] if timing in TRACK_BIAS_TOP3_TIMINGS else []
            win_extras += [bias.attach] if timing in TRACK_BIAS_WIN_TIMINGS else []
        if timing in WEIGHT_DISCOUNT_TIMINGS:
            weight = RaceWeightDiscountAttacher(WeightTableStore(weight_cache_folder_beside(self._development_root)).load(con))
            extras += [weight.attach] if timing in WEIGHT_DISCOUNT_TOP3_TIMINGS else []
            win_extras += [weight.attach] if timing in WEIGHT_DISCOUNT_WIN_TIMINGS else []
        return PredictionWorkflow(
            builder, SegmentedPrediction(ModelSegments(), self._models),
            OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(self._place_price()),
            pool_free=SegmentedPrediction(ModelSegments(), self._models / POOL_FREE_FOLDER), pace=pace,
            win_predictor=SegmentedPrediction(ModelSegments(), self._models / WIN_FOLDER),
            win_pool_free=SegmentedPrediction(ModelSegments(), self._models / POOL_FREE_FOLDER / WIN_FOLDER),
            extras=extras, win_extras=win_extras,
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
