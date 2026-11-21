"""材料の部品（ファイナルの見分け・近走・出走歴・騎手・その日の傾向・出走馬の表）を、架空の値で確かめる。"""

from __future__ import annotations

import pandas as pd

from 高知ファイナルの高配当.analysis.day_trend import DayTrend
from 高知ファイナルの高配当.analysis.distance_history import DistanceHistory
from 高知ファイナルの高配当.analysis.final_history import FinalHistory
from 高知ファイナルの高配当.analysis.final_race import FINAL, RACE_NAME_KEY, FinalRace
from 高知ファイナルの高配当.analysis.final_runners import FinalRunners
from 高知ファイナルの高配当.analysis.jockey_form import JockeyForm
from 高知ファイナルの高配当.analysis.kochi_run_features import KochiRunFeatures
from 高知ファイナルの高配当.analysis.past_runs import PastRuns
from 高知ファイナルの高配当.analysis.popularity_band import FAVORITE, LONGSHOT, MIDDLE
from 高知ファイナルの高配当.analysis.relative_position import RelativePosition

from .sample_runs import FIELD_SIZE, kochi_runs


def _one_horse(**columns: list) -> pd.DataFrame:
    """1頭の馬の、古い順の出走の行。"""
    count = len(next(iter(columns.values())))
    return pd.DataFrame({"horse_id": ["h"] * count, **columns})


def test_ファイナルレースはその日の最後のレースで名前が合うものだけ():
    runs = pd.DataFrame({
        "race_date": ["2025-01-05"] * 3 + ["2025-01-12"] * 2,
        "race_no": [1, 2, 3, 1, 2],
        "race_name": [f"{RACE_NAME_KEY}の前座", "", f"{RACE_NAME_KEY}　Ｃ３", "", "最終レース"],
    })
    assert FinalRace().mark(runs).tolist() == [False, False, True, False, False]


def test_相対位置は先頭が0で最後方が1():
    position = RelativePosition().of(pd.Series([1.0, 6.0, 11.0, None]), pd.Series([11, 11, 11, 11]))
    assert position.iloc[:3].tolist() == [0.0, 0.5, 1.0]
    assert pd.isna(position.iloc[3])


def test_近走の材料は今回の出走を含めない():
    runs = _one_horse(corner4_rel=[0.0, 1.0, 0.5, 0.2], corner1_rel=[0.0] * 4, time_diff=[2.0, 0.1, 1.0, 0.0],
                      popularity=[1, 2, 3, 4], placed=[1.0, 0.0, 1.0, 1.0], last3f_rank=[1, 2, 3, 4],
                      distance_m=[1300, 1400, 1600, 1400], class_order=[30] * 4, carried=[56.0] * 4)
    out = PastRuns().add(runs)
    assert pd.isna(out["places_recent5"].iloc[0])                    # 初めての出走は近走が無い
    assert out["places_recent5"].iloc[1:].tolist() == [1.0, 1.0, 2.0]
    assert out["corner4_rel_recent3"].iloc[3] == 0.5                 # 前の3走（0.0・1.0・0.5）の平均
    assert out["time_diff_best5"].iloc[3] == 0.1
    assert out["prev_run_distance_m"].iloc[1:].tolist() == [1300, 1400, 1600]


def test_ファイナルの出走歴は今回より前だけを数える():
    runs = _one_horse(**{FINAL: [True, False, True, True]}, placed=[1.0, 1.0, 0.0, 1.0], won=[1.0, 0.0, 0.0, 0.0])
    out = FinalHistory().add(runs)
    assert out["prev_run_final"].tolist() == [False, True, False, True]
    assert out["final_runs_before"].tolist() == [0.0, 1.0, 1.0, 2.0]
    assert out["final_places_before"].tolist() == [0.0, 1.0, 1.0, 1.0]   # ファイナルでない走の3着以内は数えない
    assert out["final_wins_before"].tolist() == [0.0, 1.0, 1.0, 1.0]


def test_同じ距離の出走歴は距離ごとに数える():
    runs = _one_horse(distance_m=[1300, 1400, 1300, 1300], placed=[1.0, 1.0, 0.0, 1.0])
    out = DistanceHistory().add(runs)
    assert out["distance_runs_before"].tolist() == [0, 0, 1, 2]
    assert out["distance_places_before"].tolist() == [0.0, 0.0, 1.0, 1.0]


def test_騎手の成績はその日より前の365日だけ():
    days = pd.to_datetime(["2024-01-01", "2025-03-01", "2025-06-01", "2025-06-01"])
    runs = pd.DataFrame({"jockey_code": ["j"] * 4, "race_date": days, "popularity": [1, 1, 1, 1],
                         "placed": [1.0, 0.0, 1.0, 1.0], "corner4_rel": [0.0, 0.4, 0.0, 0.0]})
    out = JockeyForm().add(runs)
    assert pd.isna(out["jockey_rides_365"].iloc[0])           # 前の騎乗が無い
    assert pd.isna(out["jockey_rides_365"].iloc[1])           # 1年より前の騎乗は数えない
    today = out[out["race_date"] == days[2]]
    assert today["jockey_rides_365"].tolist() == [1.0, 1.0]   # その日の騎乗は数えない
    assert today["jockey_place_rate_365"].tolist() == [0.0, 0.0]
    assert today["jockey_corner4_rel_365"].tolist() == [0.4, 0.4]


def test_その日の傾向は最終レースより前のレースだけ():
    runs = pd.DataFrame({
        "race_date": ["2025-01-05"] * 6, "race_no": [1, 1, 2, 2, 3, 3], "finish": [1, 5, 1, 2, 1, 2],
        "corner4_rel": [0.0, 1.0, 0.2, 0.4, 0.9, 0.9], "frame_no": [1, 8, 2, 3, 8, 8],
        "jockey_code": ["a", "b", "a", "b", "a", "b"], "placed": [1.0, 0.0, 1.0, 1.0, 1.0, 1.0], "won": [1.0, 0.0, 1.0, 0.0, 1.0, 0.0],
    })
    out = DayTrend().add(runs)
    last = out[out["race_no"] == 3].set_index("jockey_code")
    assert round(last["day_corner4_rel"].iloc[0], 6) == 0.2    # 1・2レースの3着以内（0.0・0.2・0.4）の平均。3レースは入らない
    assert last["day_frame"].iloc[0] == 2.0
    assert last.loc["a", "jockey_day_wins"] == 2.0             # 3レースの勝ちは数えない
    assert last.loc["b", "jockey_day_places"] == 1.0
    assert last.loc["a", "jockey_day_rides"] == 2


def test_材料を全部付けても行は増えず_ファイナルの出走馬だけ取り出せる():
    raw = kochi_runs()
    runs = KochiRunFeatures().build(raw)
    assert len(runs) == len(raw)
    runners = FinalRunners(min_heads=FIELD_SIZE).select(runs)
    assert runners[FINAL].all() and runners["race_id"].nunique() == raw["race_date"].nunique()
    assert FinalRunners(min_heads=FIELD_SIZE + 1).select(runs).empty      # 頭数が足りないレースは対象にしない


def test_出走馬の表はレースの中の順位と帯と回収率を持つ():
    runners = FinalRunners(min_heads=FIELD_SIZE).select(KochiRunFeatures().build(kochi_runs()))
    last_race = runners[runners["race_date"] == runners["race_date"].max()]
    front_most = last_race.loc[last_race["corner4_rel_recent3"].idxmin()]
    assert front_most["corner4_rank_in_race"] == 1.0
    assert (last_race["front_runners"] == (last_race["corner4_rel_recent3"] <= 0.3).sum()).all()
    by_popularity = last_race.set_index("popularity")["band"]
    assert (by_popularity[1], by_popularity[5], by_popularity[9]) == (FAVORITE, MIDDLE, LONGSHOT)
    winner = last_race[last_race["finish"] == 1].iloc[0]
    assert winner["win_return"] == 5.0 and winner["place_return"] == 2.0


def test_着順が付かなかった出走は3着以内でないと数える():
    raw = kochi_runs(days=2)
    raw["finish"] = raw["finish"].astype("Int32").mask(raw["horse_no"] == 1)      # 馬番1は競走中止（着順なし）
    runs = KochiRunFeatures().build(raw)
    stopped = runs[runs["horse_no"] == 1]
    assert (stopped["placed"] == 0.0).all() and (stopped["won"] == 0.0).all()
    assert runs[["placed", "final_places_before", "distance_places_before"]].notna().all().all()
