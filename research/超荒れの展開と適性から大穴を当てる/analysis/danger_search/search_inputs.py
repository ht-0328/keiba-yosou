"""消の線の探索に使う、時点ごとの入力（全頭の予想・1着の予想・結果と確定オッズ・荒れ具合）を読む。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.form_aptitude_top3.command.yosou_name import YOSOU_NAME
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP3_RATE, WIN_RATE
from yosou.shared.place_value import PlacePriceEstimator
from yosou.shared.repository import PlacePriceRepository, RaceDayRange

from 今週の予想.forecast_columns import MARKET_TOP3, MARKET_WIN, PROBABILITY, WIN_PROBABILITY

from 印の成績.backtest_marker import BacktestMarker
from 印の成績.prediction_file import TEST, PredictionFile
from 印の成績.race_results import RaceResults
from 印の成績.upset_file import DEFAULT_UPSET, UpsetFile
from 印の成績.win_value_attacher import WinValueAttacher

_REPORTS = Path(__file__).resolve().parents[4] / "reports"
#: 今のモデル（近走と適性から3着以内を予想）の15の区切りの予測（研究「複勝以外の回収率100超」）。時点 → （3着以内, 1着）。
PREDICTION_FILES: dict[PredictionTiming, tuple[Path, Path]] = {
    PredictionTiming.RACE_DAY: (_REPORTS / "複勝以外の回収率100超" / "predictions-2019から" / "dscore_race_day" / "top3-race_day.pkl",
                                _REPORTS / "複勝以外の回収率100超" / "predictions-2019から" / "dscore_finish_race_day" / "win-race_day.pkl"),
    PredictionTiming.DAY_BEFORE: (_REPORTS / "複勝以外の回収率100超" / "predictions-2019から" / "dscore_day_before" / "top3-day_before.pkl",
                                  _REPORTS / "複勝以外の回収率100超" / "predictions-2019から" / "dscore_day_before" / "win-day_before.pkl"),
}
#: 複勝の見込みの倍率と組の確率の重みの置き場所（道具「印の成績」の既定と同じ）。
DEFAULT_MODELS = _REPORTS / YOSOU_NAME / "models"
#: 馬の強さ（組の期待値の候補）に使う列。
HORSE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "horse_id", "horse_no", PROBABILITY, WIN_PROBABILITY, MARKET_TOP3, MARKET_WIN)


class SearchInputs:
    """時点の、道具「印の成績」と同じ入力をまとめて読む（``load``）。

    - ``tested``: 全頭の予想のテスト期間の行（印を付けるレース）。
    - ``places``: 出走の行に着順・確定オッズ・人気・払戻・複勝オッズと、オッズから見た勝率・3着以内率を付けた表（``BacktestMarker.places``）。
    - ``wins``: 1着の予想のテスト期間の行に単勝の期待値を付けた表（``WinValueAttacher``）。
    - ``upset``: 3連複の荒れ具合（レースに1つ。``UpsetFile``）。
    - ``marker``: 今週の予想と同じ決め方で印を付ける部品（当日・前日なのでオッズは使う）。
    ``extra_race_ids`` は結果を読む範囲に足すレース（人気馬の予想の行。印の成績と同じく、全頭・1着・人気馬の予測のレースの和で読む）。
    """

    def __init__(self, timing: PredictionTiming, models: Path = DEFAULT_MODELS, upset: Path = DEFAULT_UPSET) -> None:
        self.timing = timing
        self.models = Path(models)
        self._upset = Path(upset)
        form, win = PREDICTION_FILES[timing]
        self.form = PredictionFile(str(form))
        self.win = PredictionFile(str(win))
        self.tested: pd.DataFrame | None = None
        self.places: pd.DataFrame | None = None
        self.wins: pd.DataFrame | None = None
        self.upset: pd.DataFrame | None = None
        self.marker: BacktestMarker | None = None

    def load(self, con: duckdb.DuckDBPyConnection, extra_race_ids: pd.Series | None = None) -> None:
        predictions = self.form.load()
        self.tested = predictions[predictions["period"] == TEST].reset_index(drop=True)
        win_predictions = self.win.load()
        race_ids = pd.concat([self.tested["race_id"], win_predictions["race_id"], *([extra_race_ids] if extra_race_ids is not None else [])])
        state = PlacePriceRepository(self.models).load()
        self.marker = BacktestMarker(PlacePriceEstimator.from_state(state) if state is not None else None, odds_known=True)
        self.places = self.marker.places(RaceResults().read(con, race_ids))
        self.wins = WinValueAttacher().attach(win_predictions, self.places)
        self.upset = UpsetFile(self._upset).load()

    @property
    def race_ids(self) -> pd.Series:
        """印を付けるレース（重複なし）。"""
        return self.tested["race_id"].drop_duplicates().reset_index(drop=True)

    @property
    def days(self) -> RaceDayRange:
        """印を付けるレースの開催日の範囲。"""
        dates = pd.to_datetime(self.tested["race_date"])
        return RaceDayRange(dates.min().date(), dates.max().date())

    def horses(self) -> pd.DataFrame:
        """1行 = 1頭の、確率と市場の見立て（列 ``HORSE_COLUMNS``）。組の期待値の候補（印と消に依らない段）に渡す。
        ``BacktestMarker.mark`` と同じく、全頭の予想の行に結果を内側で結び、1着の予想を左から結ぶ。"""
        table = self.tested[["race_id", "race_date", "horse_id", PROBABILITY]].merge(
            self.places[["race_id", "horse_id", "horse_no", TOP3_RATE, WIN_RATE]], on=["race_id", "horse_id"], how="inner")
        table = table.merge(self.wins[["race_id", "horse_id", WIN_PROBABILITY]], on=["race_id", "horse_id"], how="left")
        return table.rename(columns={TOP3_RATE: MARKET_TOP3, WIN_RATE: MARKET_WIN})[list(HORSE_COLUMNS)]
