"""まとまり O（対戦レーティング）の作り方。部品は手で作った表で、リポジトリは合成DB で確かめる。"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from 共通 import db

from ..feature import HEAD_TO_HEAD_FEATURES, EntryRecords, WorkoutCoverage
from ..feature.group import HeadToHeadRatingFeatures
from ..feature.head_to_head import HEAD_TO_HEAD_NAMES, RatingTableBuilder
from ..feature.head_to_head.elo_race_update import EloRaceUpdate
from ..feature.head_to_head.head_to_head_columns import (
    FIELD_GAP,
    FIELD_RANK,
    FIELD_Z,
    INITIAL_RATING,
    K_FACTOR_NEW,
    LAST_CHANGE,
    RATING,
    RECENT_CHANGE,
    RUN_COUNT,
)
from ..feature.head_to_head.rating_change_columns import RatingChangeColumns
from ..feature.head_to_head.rating_history_builder import RatingHistoryBuilder
from ..repository import FactTableRepository, HeadToHeadRunRepository, TargetScope
from . import synthetic_season as season
from .synthetic_season.season_plan import JUMP_RACE

#: 新しい馬の K で、同じレーティングの3頭が走ったときの1着の上がり幅（(1 − 0.5) × 2 ÷ 2 × K）。
_HALF_K = K_FACTOR_NEW / 2


def _runs(rows: list[tuple[str, str, str, float | None]]) -> pd.DataFrame:
    """（レースID, 開催日, 馬, 着順）の並びから、出走の表を作る。"""
    return pd.DataFrame([{"race_id": race, "race_date": pd.Timestamp(day), "horse_id": horse, "finish": finish,
                          "is_target": True} for race, day, horse, finish in rows])


def test_the_seven_features_are_numbers_in_group_o_known_on_thursday():
    assert [feature.name for feature in HEAD_TO_HEAD_FEATURES] == list(HEAD_TO_HEAD_NAMES)
    assert len(HEAD_TO_HEAD_NAMES) == len(set(HEAD_TO_HEAD_NAMES)) == 7
    assert all(feature.group == "O" and feature.known_from.value == "thursday" and not feature.is_categorical
               for feature in HEAD_TO_HEAD_FEATURES)


def test_elo_update_gives_the_winner_half_k_and_sums_to_zero_for_equal_ratings():
    deltas = EloRaceUpdate().deltas(np.array([1500.0, 1500.0, 1500.0]), np.array([1.0, 2.0, 3.0]), np.full(3, K_FACTOR_NEW))
    np.testing.assert_allclose(deltas, [_HALF_K, 0.0, -_HALF_K])


def test_elo_update_counts_a_dead_heat_as_half_and_moves_less_when_the_stronger_horse_wins():
    update = EloRaceUpdate()
    tied = update.deltas(np.array([1500.0, 1500.0]), np.array([1.0, 1.0]), np.full(2, K_FACTOR_NEW))
    np.testing.assert_allclose(tied, [0.0, 0.0])
    # 400 高い馬が勝つのは見込みどおり（勝つ見込み 0.909）なので、動く幅は小さい。負けると大きく下がる
    expected_win = update.deltas(np.array([1900.0, 1500.0]), np.array([1.0, 2.0]), np.full(2, K_FACTOR_NEW))
    assert 0 < expected_win[0] < _HALF_K and expected_win[0] == pytest.approx(-expected_win[1])
    upset = update.deltas(np.array([1900.0, 1500.0]), np.array([2.0, 1.0]), np.full(2, K_FACTOR_NEW))
    assert upset[0] < -K_FACTOR_NEW / 2
    # 1頭だけなら動かない
    assert EloRaceUpdate().deltas(np.array([1500.0]), np.array([1.0]), np.array([K_FACTOR_NEW])).tolist() == [0.0]


def test_history_uses_only_the_races_before_the_day():
    runs = _runs([("r1", "2024-01-06", "A", 1), ("r1", "2024-01-06", "B", 2), ("r1", "2024-01-06", "C", 3),
                  ("r2", "2024-01-13", "A", 3), ("r2", "2024-01-13", "B", 1), ("r2", "2024-01-13", "D", 2),
                  ("r3", "2024-01-13", "C", 1), ("r3", "2024-01-13", "E", 2),
                  ("r4", "2024-01-20", "A", None), ("r4", "2024-01-20", "C", None)])
    history = RatingHistoryBuilder().build(runs).set_index(["race_id", "horse_id"])
    # 初めての日は全頭が初期値で、対戦数 0
    assert (history.loc["r1", RATING] == INITIAL_RATING).all() and (history.loc["r1", RUN_COUNT] == 0).all()
    # 次の週は、前の週の結果ぶんだけ動いている（r1 の 1着 +20・2着 0・3着 −20）。同じ日の r2 と r3 は互いを見ない
    assert history.loc[("r2", "A"), RATING] == pytest.approx(INITIAL_RATING + _HALF_K)
    assert history.loc[("r2", "B"), RATING] == pytest.approx(INITIAL_RATING)
    assert history.loc[("r3", "C"), RATING] == pytest.approx(INITIAL_RATING - _HALF_K)
    assert history.loc[("r2", "D"), RUN_COUNT] == 0 and history.loc[("r2", "A"), RUN_COUNT] == 1
    # まだ走っていないレース（着順が無い）には、その前日までの値が付く。A は r2 で3着になって下がっている
    assert history.loc[("r4", "A"), RATING] < history.loc[("r2", "A"), RATING]
    assert history.loc[("r4", "A"), RUN_COUNT] == 2 and history.loc[("r4", "C"), RUN_COUNT] == 2


def test_history_does_not_count_a_horse_without_a_finish():
    # B は競走中止（着順なし）。A と C の勝ち負けだけで更新し、B のレーティングと対戦数は動かない
    runs = _runs([("r1", "2024-01-06", "A", 1), ("r1", "2024-01-06", "B", None), ("r1", "2024-01-06", "C", 2),
                  ("r2", "2024-01-13", "A", 1), ("r2", "2024-01-13", "B", 2), ("r2", "2024-01-13", "C", 3)])
    history = RatingHistoryBuilder().build(runs).set_index(["race_id", "horse_id"])
    assert history.loc[("r2", "B"), RATING] == INITIAL_RATING and history.loc[("r2", "B"), RUN_COUNT] == 0
    assert history.loc[("r2", "A"), RATING] == pytest.approx(INITIAL_RATING + K_FACTOR_NEW / 2)
    assert history.loc[("r2", "A"), RUN_COUNT] == 1


def test_history_keeps_the_row_order_of_the_runs():
    runs = _runs([("r2", "2024-01-13", "A", 1), ("r1", "2024-01-06", "A", 1), ("r1", "2024-01-06", "B", 2),
                  ("r2", "2024-01-13", "B", 2)]).set_axis([7, 3, 5, 9])
    history = RatingHistoryBuilder().build(runs)
    assert history.index.tolist() == [7, 3, 5, 9] and history["race_id"].tolist() == runs["race_id"].tolist()
    assert history.loc[7, RATING] > history.loc[3, RATING] == INITIAL_RATING


def test_change_columns_compare_with_the_previous_and_the_fifth_last_run():
    days = pd.date_range("2024-01-06", periods=7, freq="7D")
    history = pd.DataFrame({"race_id": [f"r{index}" for index in range(7)], "horse_id": "A", "race_date": days,
                            RATING: [1500.0, 1510.0, 1530.0, 1520.0, 1540.0, 1560.0, 1550.0]})
    changes = RatingChangeColumns().build(history)
    # 初めての走はどちらも欠損値。前走での変化は1つ前との差
    assert np.isnan(changes.loc[0, LAST_CHANGE]) and np.isnan(changes.loc[0, RECENT_CHANGE])
    assert changes[LAST_CHANGE].tolist()[1:] == pytest.approx([10.0, 20.0, -10.0, 20.0, 20.0, -10.0])
    # 近5走の変化は5つ前との差（5走に満たなければ、初めての走の値との差）
    assert changes.loc[3, RECENT_CHANGE] == pytest.approx(20.0)
    assert changes.loc[5, RECENT_CHANGE] == pytest.approx(60.0) and changes.loc[6, RECENT_CHANGE] == pytest.approx(40.0)


def test_table_builder_aligns_to_the_entries_and_compares_within_the_race():
    runs = _runs([("r1", "2024-01-06", "A", 1), ("r1", "2024-01-06", "B", 2), ("r1", "2024-01-06", "C", 3),
                  ("r2", "2024-01-13", "A", None), ("r2", "2024-01-13", "B", None), ("r2", "2024-01-13", "D", None)])
    # 出走の行は r2 の3頭と、記録の無い馬 Z（取消が分かっていない行など）。index は飛び飛びでよい
    entries = pd.DataFrame({"race_id": ["r2"] * 4, "horse_id": ["A", "B", "D", "Z"]}, index=[10, 20, 30, 40])
    table = RatingTableBuilder().build(entries, runs)
    assert list(table.columns) == list(HEAD_TO_HEAD_NAMES) and table.index.tolist() == [10, 20, 30, 40]
    assert table.loc[10, RATING] == pytest.approx(INITIAL_RATING + _HALF_K) and table.loc[10, RUN_COUNT] == 1
    assert table.loc[10, FIELD_RANK] == 1 and table.loc[20, FIELD_RANK] == table.loc[30, FIELD_RANK] == 2
    # 平均との差の合計は 0、偏差は平均との差を標準偏差で割ったもの。記録の無い馬は全部欠損値で、比べにも入らない
    known = table.loc[[10, 20, 30]]
    assert known[FIELD_GAP].sum() == pytest.approx(0.0)
    np.testing.assert_allclose(known[FIELD_Z], known[FIELD_GAP] / known[RATING].std())
    assert table.loc[40].isna().all()
    assert table.loc[10, LAST_CHANGE] == pytest.approx(_HALF_K) and np.isnan(table.loc[30, RECENT_CHANGE])


def test_the_group_returns_missing_values_without_runs():
    entries = pd.DataFrame({"race_id": ["r1", "r1"], "horse_id": ["A", "B"]})
    records = EntryRecords(
        entries=entries, past_runs=pd.DataFrame(), workouts=pd.DataFrame(), workout_coverage=WorkoutCoverage.complete(),
        jockey_days=pd.DataFrame(), trainer_days=pd.DataFrame(), sire_days=pd.DataFrame(), damsire_days=pd.DataFrame(),
    )
    features = HeadToHeadRatingFeatures().build(records)
    assert list(features.columns) == list(HEAD_TO_HEAD_NAMES) and features.isna().all().all()


@pytest.fixture(scope="module")
def season_con(season_db: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """架空の1シーズンの合成DB への接続（事実表つき）。"""
    with db.open_db(season_db) as con:
        FactTableRepository(con).ensure()
        yield con


def test_repository_reads_the_flat_runs_before_the_targets_last_day(season_con):
    first_target_day = date(2024, 6, 1)
    runs = HeadToHeadRunRepository(season_con, season.FIRST_RACE_DAY).read(TargetScope.since(first_target_day))
    assert list(runs.columns) == ["race_id", "race_date", "horse_id", "finish", "is_target"]
    targets, history = runs[runs["is_target"]], runs[~runs["is_target"]]
    # 対象は 6月以降の出走、過去の出走はシーズンの初めから対象のいちばん遅い日より前で、対象のレースを含まない
    assert targets["race_date"].min() >= pd.Timestamp(first_target_day)
    assert history["race_date"].min() == pd.Timestamp(season.FIRST_RACE_DAY)
    assert history["race_date"].max() < targets["race_date"].max()
    assert not set(history["race_id"]) & set(targets["race_id"])
    # 障害のレース（レース番号 05）は入れない。開催日の順に並ぶ
    assert not runs["race_id"].str.endswith(JUMP_RACE.race_no).any()
    assert runs["race_date"].is_monotonic_increasing


def test_repository_feeds_the_group_for_a_card_before_the_race(season_con):
    runs = HeadToHeadRunRepository(season_con, season.FIRST_RACE_DAY).read(TargetScope.since(date(2024, 12, 1)))
    entries = runs[runs["is_target"]].drop_duplicates(["race_id", "horse_id"]).reset_index(drop=True)
    table = RatingTableBuilder().build(entries, runs)
    # シーズンの終わりの出走には、それまでの走から作ったレーティングが付き、同じレースの中で順位が付く
    assert table[RATING].notna().all() and (table[RUN_COUNT] > 0).mean() > 0.9
    assert (table.groupby(entries["race_id"])[FIELD_RANK].min() == 1).all()
