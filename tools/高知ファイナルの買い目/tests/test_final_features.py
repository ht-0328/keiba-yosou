"""FinalFeatures（高知の出走の表 → 予想の材料）のテスト。出走の表は架空（SampleRuns）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 高知ファイナルの買い目.final_columns import FEATURES
from 高知ファイナルの買い目.final_features import FinalFeatures

from 高知ファイナルの買い目.testing.sample_runs import HORSES, SampleRuns

SAMPLE = SampleRuns()
LAST_FINAL = SAMPLE.rid(5, 3)


def _table(runs: pd.DataFrame, focus: str | None = None) -> pd.DataFrame:
    features = FinalFeatures()
    return features.build(runs, features.popularity_rates(runs), focus)


def test_特徴量の列が全部そろう() -> None:
    table = _table(SAMPLE.build())
    assert not [column for column in FEATURES if column not in table.columns]
    assert len(table) == 6 * 3 * HORSES


def test_近走の材料は_今回より前の走だけから作る() -> None:
    table = _table(SAMPLE.build())
    horse = table[table["horse_id"] == "H301"].sort_values("race_date")
    assert np.isnan(horse["fin_m3"].iloc[0]) and horse["f_runs"].tolist() == [0, 1, 2, 3, 4, 5]
    assert horse["fin_m3"].iloc[3] == horse["finish"].iloc[:3].mean()
    assert horse["prev_is_final"].tolist() == [0, 1, 1, 1, 1, 1]


def test_その日の傾向は_そのレースより前のレースだけから作る() -> None:
    table = _table(SAMPLE.build())
    day = table[table["race_date"] == table["race_date"].max()].drop_duplicates("race_no").set_index("race_no")
    assert day["day_races"].tolist() == [0, 1, 2] and np.isnan(day.loc[1, "day_c4"]) and not np.isnan(day.loc[3, "day_c4"])


def test_これから走るレースにも材料が付き_結果の列を見ない() -> None:
    runs = SAMPLE.build(unrun=LAST_FINAL)
    runs.loc[runs["race_id"] == LAST_FINAL, "win_odds"] = [2.0 + no for no in range(HORSES)]
    table = _table(runs, focus=LAST_FINAL)
    assert len(table) == HORSES and table["day_races"].eq(2).all() and table["f_runs"].eq(5).all()
    assert table["pop_now"].tolist() == sorted(table["pop_now"]) or set(table["pop_now"]) == set(range(1, HORSES + 1))
    finished = _table(SAMPLE.build(), focus=LAST_FINAL)
    same = [column for column in FEATURES if column not in ("lm", "pop_now", "lm_gap", "pop_gap")]
    left = table.sort_values("horse_no")[same].astype(float).to_numpy()
    right = finished.sort_values("horse_no")[same].astype(float).to_numpy()
    assert np.allclose(left, right, equal_nan=True)


def test_1レースだけ作っても_全部の走で作った値と同じ() -> None:
    runs = SAMPLE.build()
    whole = _table(runs)
    whole = whole[whole["race_id"] == LAST_FINAL].sort_values("horse_no")
    one = _table(runs, focus=LAST_FINAL).sort_values("horse_no")
    assert np.allclose(one[list(FEATURES)].astype(float).to_numpy(), whole[list(FEATURES)].astype(float).to_numpy(), equal_nan=True)


def test_オッズの無い馬は材料の表から外れる() -> None:
    runs = SAMPLE.build(unrun=LAST_FINAL)
    target = runs["race_id"] == LAST_FINAL
    runs.loc[target & (runs["horse_no"] != 4), "win_odds"] = 5.0
    assert sorted(_table(runs, focus=LAST_FINAL)["horse_no"].astype(int)) == [1, 2, 3, 5, 6, 7, 8, 9, 10]
