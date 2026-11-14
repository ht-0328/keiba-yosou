"""中央の未見の予測に、印の成績と同じ決め方で印を付け、◎ の行（確率・期待値・結果・払戻）だけを残す。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from 共通 import db

from yosou.shared.place_value import PlacePriceEstimator
from yosou.shared.repository import PlacePriceRepository

from 今週の予想.danger_picker import MARKED_BANDS
from 今週の予想.forecast_columns import MARK
from 今週の予想.mark_rule import TOP_MARK

from 印の成績.backtest_marker import BacktestMarker
from 印の成績.favorite_danger_judge import FavoriteDangerJudge
from 印の成績.prediction_file import TEST, PredictionFile
from 印の成績.race_results import RaceResults
from 印の成績.win_value_attacher import WinValueAttacher

from 地方の期待度.analysis.top_picks import COLUMNS, RACE_DATE, RACE_ID, YEAR


class JraTopPicks:
    """``form``・``win``・``danger`` は研究「既存モデルの改善」の予測の名前（``<予想>/<作り方>``。7つの区切りのテスト期間の行が未見の予測）、
    ``models`` は複勝の見込みの倍率（``place_price.json``）のある学習済みモデルの置き場所。
    ◎ の決め方は道具「印の成績」の表13 と同じ（危険な人気馬を消にしてから、単勝 30倍以下で単勝の期待値が1位の馬。オッズ・払戻は確定の値）。
    作った表は ``cache`` に pickle でとっておき、``load`` は無いときだけ元DB を読む（全レースの成績を読むので数分かかる）。"""

    def __init__(self, form: str, win: str, danger: str, models: Path, cache: Path) -> None:
        self._form = form
        self._win = win
        self._danger = danger
        self._models = Path(models)
        self._cache = Path(cache)

    def load(self, db_path: Path | None = None, rebuild: bool = False) -> pd.DataFrame:
        """◎ の行（1行 = 1レース。列は ``COLUMNS``）。"""
        path = self.cache_path()
        if path.is_file() and not rebuild:
            return pd.read_pickle(path)
        return self.build(db_path)

    def build(self, db_path: Path | None = None) -> pd.DataFrame:
        predictions = PredictionFile(self._form).load()
        tested = predictions[predictions["period"] == TEST]
        win_predictions = PredictionFile(self._win).load()
        favorites = PredictionFile(self._danger).load()
        marker = BacktestMarker(self._estimator(), odds_known=True)
        print(f"{self._form} のテスト期間 {tested[RACE_ID].nunique():,} レースの成績を元DB から読みます", file=sys.stderr, flush=True)
        with db.open_db(db_path, default=db.JRA) as con:
            race_ids = pd.concat([tested[RACE_ID], favorites[RACE_ID], win_predictions[RACE_ID]])
            places = marker.places(RaceResults().read(con, race_ids))
        dangers, _ = FavoriteDangerJudge(tuple(MARKED_BANDS)).judge(favorites, places)
        wins = WinValueAttacher().attach(win_predictions, places)
        marked = marker.mark(tested, places, dangers, wins, None, None)
        self._cache.mkdir(parents=True, exist_ok=True)
        marked.to_pickle(self.all_rows_path())   # ◎ の選び方を変えて比べるための全頭の行
        tops = marked[marked[MARK] == TOP_MARK].copy()
        tops[YEAR] = pd.to_datetime(tops[RACE_DATE]).dt.year
        table = tops[list(COLUMNS)].reset_index(drop=True)
        path = self.cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        table.to_pickle(path)
        print(f"◎ {len(table):,} レース → {path}", file=sys.stderr, flush=True)
        return table

    def cache_path(self) -> Path:
        return self._cache / f"◎-{self._form.replace('/', '_')}.pkl"

    def all_rows_path(self) -> Path:
        """印を付けた全頭の行（``BacktestMarker.mark`` の戻り値そのまま）の置き場所。"""
        return self._cache / f"全頭-{self._form.replace('/', '_')}.pkl"

    def _estimator(self) -> PlacePriceEstimator | None:
        state = PlacePriceRepository(self._models).load()
        return PlacePriceEstimator.from_state(state) if state is not None else None
