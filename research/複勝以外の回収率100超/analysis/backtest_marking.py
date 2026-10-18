"""区切りの予測に、道具「印の成績」と同じ決め方で印と期待度を付ける（馬ごとの表）。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.place_value import PlacePriceEstimator
from yosou.shared.repository import PlacePriceRepository

from 今週の予想.danger_picker import MARKED_BANDS
from 印の成績.backtest_marker import BacktestMarker
from 印の成績.favorite_danger_judge import FavoriteDangerJudge
from 印の成績.odds_snapshot_repository import OddsSnapshotRepository
from 印の成績.pool_win_reader import PoolWinReader
from 印の成績.prediction_file import TEST, PredictionFile
from 印の成績.race_results import RaceResults
from 印の成績.win_value_attacher import WinValueAttacher

#: 当日の予想の予測のファイル（``early_years.py`` の合わせた予測の置き場所の下）。
FORM, WIN, DANGER = "dscore_race_day/top3-race_day.pkl", "dscore_finish_race_day/win-race_day.pkl", "favorites_out_of_top3/people_market.pkl"


class BacktestMarking:
    """当日の予想の予測（3着以内・1着・危険な人気馬。``predictions`` の下）のテスト期間に、道具「印の成績」（``mark_stats.py``）と同じ部品で
    印（◎○▲△☆注消）とレースの期待度を付けた、1頭1行の表を返す。複勝の見込みの倍率は ``models`` の ``place_price.json``。
    組の期待値の買い目を作るのに使う列（``race_id``・``horse_no``・3着以内と1着の確率・市場の見立て・印・期待度・開催日・区切り）を持つ。
    """

    def __init__(self, predictions: Path, models: Path) -> None:
        self._predictions = Path(predictions)
        self._models = Path(models)

    def mark(self, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        predictions = PredictionFile(str(self._predictions / FORM)).load()
        tested = predictions[predictions["period"] == TEST]
        state = PlacePriceRepository(self._models).load()
        marker = BacktestMarker(PlacePriceEstimator.from_state(state) if state is not None else None, odds_known=True)
        favorites = PredictionFile(str(self._predictions / DANGER)).load()
        wins = PredictionFile(str(self._predictions / WIN)).load()
        race_ids = tested["race_id"].drop_duplicates()
        places = marker.places(RaceResults().read(con, pd.concat([tested["race_id"], favorites["race_id"], wins["race_id"]])))
        pools = PoolWinReader().read(con, race_ids)
        movements = OddsSnapshotRepository().read(con, race_ids)
        dangers, _ = FavoriteDangerJudge(tuple(MARKED_BANDS)).judge(favorites, places)
        marked = marker.mark(tested, places, dangers, WinValueAttacher().attach(wins, places), pools, movements)
        return marked.assign(race_id=marked["race_id"].astype(str))
