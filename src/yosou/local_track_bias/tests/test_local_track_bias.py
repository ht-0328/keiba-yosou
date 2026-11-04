"""地方の当日の馬場傾向（前らしさの見込み・年ごとの U・予測時の見込み・一覧）。手で作った表と、地方の合成DB で確かめる。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from 共通 import db

from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import local_season as season
from yosou.track_bias import TRACK_BIAS_NAMES, BiasRunRepository, names

from ..features import LOCAL_TRACK_BIAS_FEATURES
from ..front_position import FRONT_POSITION, FrontPosition
from ..local_bias_history import LocalBiasHistory
from ..local_front_forecast import LocalFrontForecast
from ..repository import PastPositionRepository


def _runs(rows: list[tuple[str, str, str, float | None, int]]) -> pd.DataFrame:
    """(race_id, 開催日, 馬ID, 4コーナーの順位, 頭数) の並びから、傾きの元の表の要る列だけを作る。"""
    return pd.DataFrame({
        "race_id": [row[0] for row in rows], "race_date": pd.to_datetime([row[1] for row in rows]),
        "horse_id": [row[2] for row in rows], "corner4": [row[3] for row in rows], "field_size": [row[4] for row in rows],
    })


def test_前らしさの見込みは_直近3走の4コーナーの位置の平均で_初出走は欠損値():
    runs = _runs([
        ("r1", "2024-01-01", "h1", 1, 11),          # 位置 0.0
        ("r2", "2024-02-01", "h1", 6, 11),          # 位置 0.5
        ("r3", "2024-03-01", "h1", None, 11),       # 順位なし（数えない）
        ("r4", "2024-04-01", "h1", 11, 11),         # 位置 1.0
        ("r5", "2024-05-01", "h1", 3, 11),          # 位置 0.2
        ("r1", "2024-01-01", "h2", 11, 11),         # 別の馬
    ])
    table = FrontPosition().of(runs.iloc[::-1])     # 並びが逆でも同じ結果（index で返す）
    got = table.set_index(["race_id", "horse_id"])[FRONT_POSITION]
    assert np.isnan(got[("r1", "h1")]) and np.isnan(got[("r1", "h2")])            # 初出走
    assert got[("r2", "h1")] == 0.0                                                # 直前の1走
    assert got[("r3", "h1")] == 0.25                                               # 順位なしの走にも、前の2走の平均が付く
    assert got[("r4", "h1")] == 0.25                                               # 順位なしの走は数えない
    assert abs(got[("r5", "h1")] - 0.5) < 1e-9                                     # 直近3走（0.0・0.5・1.0）の平均
    assert list(table.index) == list(runs.iloc[::-1].index) and list(table.columns) == ["race_id", "horse_id", FRONT_POSITION]


def test_一覧は中央と同じ5個で_当日から分かる():
    assert tuple(feature.name for feature in LOCAL_TRACK_BIAS_FEATURES) == TRACK_BIAS_NAMES
    assert all(feature.known_from is PredictionTiming.RACE_DAY for feature in LOCAL_TRACK_BIAS_FEATURES)


def test_合成DBの全出走にUが付き_当日は先に終わったレースだけを数える(local_season_db: Path):
    with db.open_db(local_season_db) as con:
        runs = BiasRunRepository(con).read(date(2023, 1, 1))
    assert not runs.empty
    history = LocalBiasHistory().of(PredictionTiming.RACE_DAY, runs)
    assert set(TRACK_BIAS_NAMES) <= set(history.columns) and len(history) == len(runs)
    assert history[names.INNER_SLOPE_FEATURE].notna().all()                       # 使う傾きは過去の傾きが 0 でも値になる
    assert history[names.INNER_PART].notna().mean() > 0.9                          # 内の分は馬番があれば付く
    # 最初の開催日の 1R は、当日の先のレースも前の日のレースも無いので、使う傾きは過去の傾き（最初の年は 0）
    first_day = runs[names.RACE_DATE].min()
    first_race = runs[(runs[names.RACE_DATE] == first_day) & (runs[names.RACE_NO] == runs[runs[names.RACE_DATE] == first_day][names.RACE_NO].min())]
    rows = history[history[names.RACE_ID].isin(first_race[names.RACE_ID])]
    assert (rows[names.INNER_SLOPE_FEATURE] == 0.0).all() and (rows[names.INNER_PART] == 0.0).all()
    # 前日の時点は、当日のレースを数えない（同じ日の 1R と 12R で使う傾きが同じ）
    before = LocalBiasHistory().of(PredictionTiming.DAY_BEFORE, runs)
    by_race = before.groupby(names.RACE_ID)[names.INNER_SLOPE_FEATURE].first()
    some_day = runs[runs[names.RACE_DATE] > first_day].iloc[0][names.RACE_DATE]
    day_races = runs[runs[names.RACE_DATE] == some_day].drop_duplicates(names.RACE_ID)
    assert by_race.reindex(day_races[names.RACE_ID]).nunique() == 1


def test_予測時の前らしさの見込みは_レースより前の走から読む(local_season_db: Path):
    with db.open_db(local_season_db) as con:
        forecast = LocalFrontForecast().run(con, season.CARD_RACE_ID, PredictionTiming.RACE_DAY)
        runs = BiasRunRepository(con).read(date(2023, 1, 1))
        positions = PastPositionRepository(con).read(date(2000, 1, 1), ["x"])
    assert list(forecast.columns) == ["horse_id", FRONT_POSITION] and len(forecast) >= 7
    known = forecast[FRONT_POSITION].dropna()
    assert not known.empty and known.between(0.0, 1.0).all()
    # 学習データの作り方（FrontPosition）と同じ値になる: 出馬表のレースの馬のうち、その前に走った馬で比べる
    history = FrontPosition().of(runs)
    horse = forecast[forecast[FRONT_POSITION].notna()].iloc[0]
    earlier = history[(history["horse_id"] == horse["horse_id"])].join(runs[["race_date"]])
    last = earlier.sort_values("race_date").iloc[-1]
    with db.open_db(local_season_db) as con:
        again = PastPositionRepository(con).read(pd.Timestamp(last["race_date"]).date(), [horse["horse_id"]])
    assert abs(float(again[FRONT_POSITION].iloc[0]) - float(last[FRONT_POSITION])) < 1e-9
    assert positions.empty and list(positions.columns) == ["horse_id", FRONT_POSITION]
