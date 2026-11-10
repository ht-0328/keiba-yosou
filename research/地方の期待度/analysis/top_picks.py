"""地方の未見の予測に、印の成績と同じ決め方で印を付け、◎ の行（確率・期待値・結果・払戻）だけを残す。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from 共通 import db

from yosou.shared.feature import PredictionTiming
from yosou.shared.place_value import PlacePriceEstimator
from yosou.shared.repository import PlacePriceRepository

from 今週の予想.forecast_columns import MARK, PLACE_VALUE, PROBABILITY, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK

from 印の成績.backtest_marker import BacktestMarker
from 印の成績.favorite_danger_judge import COLUMNS as DANGER_COLUMNS
from 印の成績.prediction_file import TEST, PredictionFile
from 印の成績.race_results import RaceResults
from 印の成績.win_value_attacher import WinValueAttacher

#: 時点 → backtest の予測のファイルの名前（``<名前>.pkl`` が3着以内、``<名前>-1着.pkl`` が1着）。
FILE_NAMES: dict[PredictionTiming, str] = {
    PredictionTiming.THURSDAY: "thursday", PredictionTiming.DAY_BEFORE: "day_before", PredictionTiming.RACE_DAY: "race_day",
}
#: ◎ の行に残す列。
RACE_ID, RACE_DATE, YEAR = "race_id", "race_date", "year"
FINISH, POPULARITY, WIN_ODDS, WIN_PAYOUT, PLACE_PAYOUT, FIELD_SIZE = "finish", "popularity", "win_odds", "win_payout", "place_payout", "field_size"
COLUMNS: tuple[str, ...] = (RACE_ID, RACE_DATE, YEAR, WIN_PROBABILITY, WIN_VALUE, PROBABILITY, PLACE_VALUE,
                            FINISH, POPULARITY, WIN_ODDS, WIN_PAYOUT, PLACE_PAYOUT, FIELD_SIZE)


class TopPicks:
    """``predictions`` は地方の予想モデルの backtest が書いた予測の置き場所（``predictions-2024検証`` など。テスト期間の行が未見の予測）、
    ``models`` は複勝の見込みの倍率（``place_price.json``）のある学習済みモデルの置き場所。
    ◎ の決め方は通知と同じ（``MarkRule``。単勝 30倍以下で単勝の期待値が1位。地方には危険な人気馬の判定が無い）。オッズ・払戻は確定の値。
    作った表は ``cache`` に pickle でとっておき、``load`` は無いときだけ元DB を読む（地方の全成績の事実表を作るので十数分かかる）。"""

    def __init__(self, predictions: Path, models: Path, cache: Path) -> None:
        self._predictions = Path(predictions)
        self._models = Path(models)
        self._cache = Path(cache)

    def load(self, timing: PredictionTiming, db_path: Path | None = None, rebuild: bool = False) -> pd.DataFrame:
        """1時点の ◎ の行（1行 = 1レース。列は ``COLUMNS``）。"""
        path = self.cache_path(timing)
        if path.is_file() and not rebuild:
            return pd.read_pickle(path)
        return self.build([timing], db_path)[timing]

    def build(self, timings: Sequence[PredictionTiming], db_path: Path | None = None) -> dict[PredictionTiming, pd.DataFrame]:
        """元DB を1回開いて、時点ごとの ◎ の行を作り、pickle にとっておく（時点が複数でも事実表は1回だけ作る）。"""
        loaded = {timing: self._read_predictions(timing) for timing in timings}
        marker = BacktestMarker(self._estimator(), odds_known=True)
        with db.open_db(db_path, default=db.LOCAL) as con:
            race_ids = pd.concat([frame[RACE_ID] for pair in loaded.values() for frame in pair])
            results = RaceResults().read(con, race_ids)
        places = marker.places(results)
        built = {}
        for timing, (tested, win) in loaded.items():
            wins = WinValueAttacher().attach(win, places)
            marked = marker.mark(tested, places, pd.DataFrame(columns=list(DANGER_COLUMNS)), wins, None, None)
            tops = marked[marked[MARK] == TOP_MARK].copy()   # 頭数（field_size）は結果の行から付いている
            tops[YEAR] = pd.to_datetime(tops[RACE_DATE]).dt.year
            table = tops[list(COLUMNS)].reset_index(drop=True)
            path = self.cache_path(timing)
            path.parent.mkdir(parents=True, exist_ok=True)
            table.to_pickle(path)
            print(f"{timing.label}: ◎ {len(table):,} レース → {path}", file=sys.stderr, flush=True)
            built[timing] = table
        return built

    def cache_path(self, timing: PredictionTiming) -> Path:
        return self._cache / f"◎-{self._predictions.name}-{FILE_NAMES[timing]}.pkl"

    def _read_predictions(self, timing: PredictionTiming) -> tuple[pd.DataFrame, pd.DataFrame]:
        """（3着以内のテスト期間の行, 1着の全部の行）。"""
        name = FILE_NAMES[timing]
        form = PredictionFile(str(self._predictions / f"{name}.pkl")).load()
        win = PredictionFile(str(self._predictions / f"{name}-1着.pkl")).load()
        tested = form[form["period"] == TEST]
        if tested.empty:
            raise LookupError(f"テスト期間の行がありません: {self._predictions / name}.pkl")
        return tested, win

    def _estimator(self) -> PlacePriceEstimator | None:
        state = PlacePriceRepository(self._models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None
