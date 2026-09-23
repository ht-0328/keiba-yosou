"""契約: 材料表は、3つの1頭ごとの予測を1つの runners にし、レースごとの本命・荒れ具合・重賞・開催週を races にまとめる。"""

import numpy as np
import pandas as pd
import pytest

from yosou.upset_level.dataset import BetType

from 馬券の買い方の検証.analysis import column_names as names
from 馬券の買い方の検証.analysis.race_material import RaceMaterials, RaceTableBuilder, RaceWeek, RunnerTableBuilder

_RACE_1, _RACE_2 = "2025070605010101", "2025070605010102"


def _form():
    return pd.DataFrame({
        names.RACE_ID_JA: [_RACE_1] * 3 + [_RACE_2] * 2, "開催日": pd.to_datetime(["2025-07-06"] * 5),
        names.HORSE_NO_JA: [1, 2, 3, 1, 2], "確定着順": [1, 2, 3, 2, 1], "確定の単勝オッズ": [2.0, 4.5, 15.0, 3.0, 2.5],
        "確定の単勝人気": [1, 2, 3, 2, 1], "単勝の払戻": [200, 0, 0, 0, 250], "複勝の払戻": [110, 180, 400, 150, 120],
        names.FORM_PROBABILITY_JA: [0.6, 0.5, 0.2, 0.55, 0.55],
    })


def _favorites():
    return pd.DataFrame({names.RACE_ID_JA: [_RACE_1, _RACE_1, _RACE_2], names.HORSE_NO_JA: [1, 2, 1],
                         names.DANGER_PROBABILITY_JA: [0.3, 0.5, 0.7]})


def _longshots():
    return pd.DataFrame({names.RACE_ID_JA: [_RACE_1], names.HORSE_NO_JA: [3], names.LONGSHOT_PROBABILITY_JA: [0.2],
                         names.LONGSHOT_ZONE_JA: ["中穴"]})


def _upset():
    rows = [(race, bet.label, value) for race, value in ((_RACE_1, 0.4), (_RACE_2, 0.7)) for bet in BetType]
    return pd.DataFrame(rows, columns=[names.RACE_ID_JA, names.BET_JA, names.UPSET_OR_MORE_JA])


def _facts():
    return pd.DataFrame({
        names.RACE_ID: [_RACE_1, _RACE_2, "2025070605010103"], names.RACE_DATE: pd.to_datetime(["2025-07-06"] * 3),
        names.VENUE_CODE: ["05"] * 3, names.RACE_NO: [1, 2, 3], names.SURFACE: ["芝", "芝", "障害"], names.DISTANCE_M: [1600] * 3,
        names.CLASS_ORDER: [5, 10, 5], names.GRADE_CODE: ["", "A", ""], names.FIELD_SIZE: [16, 12, 10],
    })


def test_runner_table_merges_three_predictions():
    runners = RunnerTableBuilder().build(_form(), _favorites(), _longshots())
    assert list(runners.columns) == [
        names.RACE_ID, names.RACE_DATE, names.HORSE_NO, names.FINISH, names.WIN_ODDS, names.POPULARITY, names.WIN_PAYOUT,
        names.PLACE_PAYOUT, names.FORM_PROB, names.DANGER_PROB, names.LONGSHOT_PROB, names.LONGSHOT_ZONE,
    ]
    first = runners[runners[names.RACE_ID] == _RACE_1].set_index(names.HORSE_NO)
    assert first.loc[3, names.DANGER_PROB] != first.loc[3, names.DANGER_PROB]  # 人気馬でない → 欠損
    assert first.loc[3, names.LONGSHOT_ZONE] == "中穴" and first.loc[1, names.LONGSHOT_PROB] != first.loc[1, names.LONGSHOT_PROB]


def test_race_table_has_favorite_upset_grade_and_week():
    runners = RunnerTableBuilder().build(_form(), _favorites(), _longshots())
    races = RaceTableBuilder().build(runners, _upset(), _facts()).set_index(names.RACE_ID)
    assert list(races.index) == [_RACE_1, _RACE_2]  # 予測の無い障害レースは入らない
    assert races.loc[_RACE_1, names.FAVORITE_NO] == 1 and races.loc[_RACE_1, names.FAVORITE_PROB] == 0.6
    assert races.loc[_RACE_2, names.FAVORITE_NO] == 2  # 同点は人気上位（2番の馬が1番人気）
    assert np.isnan(races.loc[_RACE_2, names.FAVORITE_DANGER])  # 2番の馬は人気馬の予測に無い
    assert races.loc[_RACE_1, names.upset_column(BetType.TRIO)] == 0.4 and races.loc[_RACE_2, "upset_win"] == 0.7
    assert bool(races.loc[_RACE_2, names.IS_GRADED]) is True and bool(races.loc[_RACE_1, names.IS_GRADED]) is False
    assert races.loc[_RACE_1, names.WEEK] == "2025-07-05"


def test_race_week_starts_on_saturday():
    week = RaceWeek()
    assert week.key("2025-07-05") == "2025-07-05"   # 土
    assert week.key("2025-07-06") == "2025-07-05"   # 日
    assert week.key("2025-07-07") == "2025-07-05"   # 月（振替）
    assert week.key("2025-07-11") == "2025-07-05"   # 金
    assert week.key("2025-07-12") == "2025-07-12"   # 次の土


def test_materials_slice_by_day_and_give_runners_per_race():
    runners = RunnerTableBuilder().build(_form(), _favorites(), _longshots())
    races = RaceTableBuilder().build(runners, _upset(), _facts())
    materials = RaceMaterials(races, runners)
    assert materials.race_ids == [_RACE_1, _RACE_2]
    assert list(materials.runners_of(_RACE_1)[names.HORSE_NO]) == [1, 2, 3]
    assert materials.runners_of("no-such-race").empty
    later = materials.between(pd.Timestamp("2025-08-01").date(), pd.Timestamp("2025-08-31").date())
    assert later.race_ids == [] and later.runners.empty
    with pytest.raises(KeyError):
        materials.races.set_index(names.RACE_ID).loc["2025070605010103"]
