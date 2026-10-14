"""材料の締めの日（``as_of_date``。特別登録の予想の設計書 11 の 6）を守る共通の部品。手で作った表と合成DB で確かめる。"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from 共通 import db

from ..dataset import RowsUntil, TrainingData
from ..feature import FeatureCatalog
from ..feature.ability.ability_columns import WIN_PRIOR
from ..feature.ability.cumulative_record_rates import CumulativeRecordRates
from ..feature.ability.material_cutoff import MaterialCutoff
from ..feature.ability.recent_people_rates import RecentPeopleRates
from ..feature.head_to_head.head_to_head_columns import INITIAL_RATING, RATING
from ..feature.head_to_head.rating_history_builder import RatingHistoryBuilder
from ..repository import FactTableRepository, TargetScope, WorkoutSummaryRepository
from ..repository.target_scope import AS_OF_COLUMN
from . import synthetic_season as season

#: 土曜（結果が出る日）と日曜（予測するレースの日）、その週の月曜（締めの日）。
_MONDAY, _SATURDAY, _SUNDAY = "2024-01-01", "2024-01-06", "2024-01-07"


def _runs(rows: list[tuple[str, str, str, float | None, str | None]]) -> pd.DataFrame:
    """（レースID, 開催日, 騎手, 着順, 締めの日）の並びから、出走の表を作る。馬はレースごとに別。"""
    return pd.DataFrame([{"race_id": race, "horse_id": f"{race}-{jockey}", "race_date": pd.Timestamp(day), "jockey_code": jockey,
                          "trainer_code": jockey, "finish": finish, "as_of_date": pd.Timestamp(as_of) if as_of else pd.NaT}
                         for race, day, jockey, finish, as_of in rows])


def test_the_cutoff_is_the_as_of_date_when_present_and_the_day_before_otherwise():
    rows = pd.DataFrame({"race_date": pd.to_datetime([_SUNDAY, _SUNDAY]), "as_of_date": [pd.Timestamp(_MONDAY), pd.NaT]})
    cutoff = MaterialCutoff().of(rows)
    assert list(cutoff.dt.date) == [date(2024, 1, 1), date(2024, 1, 6)]
    assert list(MaterialCutoff().next_day_of(rows).dt.date) == [date(2024, 1, 2), date(2024, 1, 7)]
    assert list(MaterialCutoff().of(rows[["race_date"]]).dt.date) == [date(2024, 1, 6)] * 2


def test_cumulative_rates_stop_at_the_as_of_date():
    # 騎手 J1 は土曜に勝った。日曜の行は、締めの日が月曜なら土曜の勝ちを数えず、締めの日が無ければ数える
    runs = _runs([("sat", _SATURDAY, "J1", 1, None), ("sun_cut", _SUNDAY, "J1", 3, _MONDAY), ("sun", _SUNDAY, "J1", 2, None)])
    rates = CumulativeRecordRates().build(runs, ("jockey_code",), "騎手").set_index("race_id")
    assert rates.loc["sun_cut", "騎手_出走数"] == 0 and rates.loc["sun_cut", "騎手_勝率"] == pytest.approx(WIN_PRIOR)
    assert rates.loc["sun", "騎手_出走数"] == 1 and rates.loc["sun", "騎手_勝率"] == pytest.approx((1 + 100 * WIN_PRIOR) / 101)


def test_recent_rates_stop_at_the_as_of_date():
    runs = _runs([("sat", _SATURDAY, "J1", 1, None), ("sun_cut", _SUNDAY, "J1", 3, _MONDAY), ("sun", _SUNDAY, "J1", 2, None)])
    rates = RecentPeopleRates().build(runs, runs).set_index("race_id")
    assert rates.loc["sun_cut", "騎手_1年_勝率"] == pytest.approx(WIN_PRIOR)
    assert rates.loc["sun", "騎手_1年_勝率"] > WIN_PRIOR


def test_rating_history_writes_the_rating_as_of_the_cutoff_and_updates_on_the_race_day():
    # 馬 A は土曜に B に勝った。日曜の A の行は、締めの日が月曜ならまだ初期値、締めの日が無ければ上がっている
    rows = [("sat", _SATURDAY, "A", 1.0, None), ("sat", _SATURDAY, "B", 2.0, None),
            ("sun_cut", _SUNDAY, "A", None, _MONDAY), ("sun", _SUNDAY, "A", None, None)]
    runs = pd.DataFrame([{"race_id": race, "race_date": pd.Timestamp(day), "horse_id": horse, "finish": finish,
                          "as_of_date": pd.Timestamp(as_of) if as_of else pd.NaT, "is_target": True}
                         for race, day, horse, finish, as_of in rows])
    history = RatingHistoryBuilder().build(runs).set_index("race_id")
    assert history.loc["sun_cut", RATING] == INITIAL_RATING
    assert history.loc["sun", RATING] > INITIAL_RATING
    # 締めの日の列が無くても同じ（開催日の前日の時点）
    plain = RatingHistoryBuilder().build(runs.drop(columns=["as_of_date"])).set_index("race_id")
    assert plain.loc["sun_cut", RATING] == plain.loc["sun", RATING] > INITIAL_RATING


def test_rows_until_drops_the_rows_on_and_after_the_end():
    ids = pd.DataFrame({"レースID": ["a", "b", "c"], "開催日": pd.to_datetime(["2024-01-06", "2024-06-30", "2024-07-01"])})
    data = TrainingData(ids, pd.DataFrame({"x": [1.0, 2.0, 3.0]}), pd.DataFrame({"y": [0, 1, 0]}), pd.DataFrame(index=ids.index),
                        FeatureCatalog(()), "y")
    kept = RowsUntil(date(2024, 7, 1)).keep(None, data)
    assert list(kept.ids["レースID"]) == ["a", "b"] and len(RowsUntil(None).keep(None, data)) == 3


def test_target_scope_carries_the_as_of_column_and_expression():
    plain = TargetScope.since(date(2024, 1, 1))
    cut = TargetScope.since(date(2024, 1, 1), "CAST(race_date AS DATE) - 5")
    assert plain.as_of_column is None and plain.as_of_expr() == "NULL::DATE"
    assert cut.as_of_column == AS_OF_COLUMN and AS_OF_COLUMN in cut.relation and AS_OF_COLUMN in cut.as_of_expr("t")
    assert TargetScope.of_table("entries", AS_OF_COLUMN).as_of_column == AS_OF_COLUMN


def test_workout_summary_counts_up_to_the_as_of_date(season_db):
    # 合成DB の調教は開催日の3日前と10日前。締めの日を開催日の5日前にすると、3日前の調教は数えない
    with db.open_db(season_db) as con:
        FactTableRepository(con).ensure()
        repository = WorkoutSummaryRepository(con)
        plain = repository.read(TargetScope.since(date(2024, 12, 1))).set_index(["race_id", "horse_id"])
        cut = repository.read(TargetScope.since(date(2024, 12, 1), "CAST(race_date AS DATE) - 5")).set_index(["race_id", "horse_id"])
    plain_counts = plain["坂路_本数30日"].fillna(0) + plain["ウッド_本数30日"].fillna(0)
    cut_counts = (cut["坂路_本数30日"].fillna(0) + cut["ウッド_本数30日"].fillna(0)).reindex(plain_counts.index)
    assert (plain_counts > 0).all() and (cut_counts <= plain_counts).all() and (cut_counts < plain_counts).any()
    assert season.FIRST_RACE_DAY < date(2024, 12, 1)
