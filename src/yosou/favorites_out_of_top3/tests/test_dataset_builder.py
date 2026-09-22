"""人気馬の選び方（設計書 06 の図1・08 の 3）と、目的変数の付け方（設計書 10）。

行の選び方と目的変数は DB を使わず、手で作った出走の行で確かめる。最後に、合成DB から作った学習データで、
同じ決まりが通しでも守られていることを確かめる。
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import pytest

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import FINISH, POPULARITY

from ..dataset import (
    IS_FAVORITE,
    OUT_OF_TOP3,
    FavoriteRule,
    FavoriteSelector,
    OutOfTop3TargetBuilder,
)
from ..feature import CATALOG

RACE = "2024060105010101"
RACE_DAY = date(2024, 6, 1)
TRAIN_FIRST_DAY = date(2024, 1, 1)


def _runner(popularity: int | None, *, race_id: str = RACE, ran: bool = True, surface: str = "芝",
            finish: int | None = 1, day: date = RACE_DAY) -> dict[str, Any]:
    """出走の行1つ。行を選ぶのに使う列だけを入れる。"""
    return {
        "race_id": race_id, "race_date": pd.Timestamp(day), "horse_id": f"{race_id}-{popularity}",
        "surface": surface, "ran": ran, "popularity": popularity, "finish": finish,
    }


def _field(size: int, **values: Any) -> pd.DataFrame:
    """``size`` 頭立てのレース1つ（1番人気から順に並べる）。"""
    return pd.DataFrame([_runner(rank, **values) for rank in range(1, size + 1)])


def _selector() -> FavoriteSelector:
    return FavoriteSelector(FavoriteRule())


@pytest.mark.parametrize(("field_size", "last"), [(7, 3), (13, 3), (14, 5), (18, 5)])
def test_favorite_range_widens_from_14_runners(field_size: int, last: int):
    assert FavoriteRule().popularity_range(field_size) == (1, last)


@pytest.mark.parametrize(("popularity", "field_size", "expected"), [
    (3, 13, True), (4, 13, False), (5, 14, True), (6, 14, False), (1, 7, True),
])
def test_favorite_judgement_at_the_boundary(popularity: int, field_size: int, expected: bool):
    assert FavoriteRule().is_favorite(popularity, field_size) is expected


def test_missing_popularity_is_not_a_favorite():
    # 人気が分からない馬は、人気馬にしない（1〜5番人気かどうかを決められないため）
    assert FavoriteRule().is_favorite(None, 16) is False
    assert FavoriteRule().is_favorite(float("nan"), 16) is False


def test_training_samples_keep_every_flat_runner_with_the_favorite_flag():
    # レース内順位を全出走馬から計算するので、人気馬でない行もいったんは残す（設計書 08 の 3）
    entries = _field(14)
    samples = _selector().training_samples(entries, TRAIN_FIRST_DAY)
    assert len(samples) == 14
    assert samples[IS_FAVORITE].tolist() == [True] * 5 + [False] * 9


def test_training_samples_drop_jumps_scratches_and_the_warmup_period():
    entries = pd.DataFrame([
        _runner(1),
        _runner(2, race_id="2024060105010102", surface="障害"),
        _runner(3, ran=False),
        _runner(4, race_id="2023060105010101", day=date(2023, 6, 1)),
    ])
    samples = _selector().training_samples(entries, TRAIN_FIRST_DAY)
    assert samples["popularity"].tolist() == [1]


def test_keep_samples_leaves_only_the_favorites():
    selector = _selector()
    samples = selector.training_samples(_field(10), TRAIN_FIRST_DAY)
    kept = selector.keep_samples(samples)
    assert kept["popularity"].tolist() == [1, 2, 3]
    assert kept.index.tolist() == [0, 1, 2]


def test_field_size_counts_the_horses_that_ran():
    # 16頭登録でも、2頭が取消なら 14頭立て。14頭以上なので 1〜5番人気が人気馬になる
    entries = pd.concat([_field(14), pd.DataFrame([_runner(15, ran=False), _runner(16, ran=False)])])
    samples = _selector().training_samples(entries.reset_index(drop=True), TRAIN_FIRST_DAY)
    assert samples[IS_FAVORITE].sum() == 5


def test_prediction_stops_when_no_popularity_is_known():
    # 確定前のレースは、元DB の単勝人気が空。利用者に --pops で渡してもらう
    entries = pd.DataFrame([_runner(None) for _ in range(10)])
    with pytest.raises(ValueError, match="--pops"):
        _selector().prediction_runners(entries, RACE)


def test_prediction_stops_when_no_favorite_runs():
    # 6番人気と7番人気の2頭しか人気が分からないレース（10頭立てなら 1〜3番人気が対象）
    entries = pd.DataFrame([_runner(6), _runner(7)])
    with pytest.raises(LookupError, match="人気馬がいません"):
        _selector().prediction_runners(entries, RACE)


def test_prediction_stops_for_jump_races_and_empty_fields():
    with pytest.raises(ValueError, match="障害"):
        _selector().prediction_runners(_field(10, surface="障害"), RACE)
    with pytest.raises(LookupError, match="出走する馬がいません"):
        _selector().prediction_runners(_field(10, ran=False), RACE)


@pytest.mark.parametrize(("finish", "expected"), [(1, 0), (3, 0), (4, 1), (16, 1), (None, 1)])
def test_target_is_one_when_the_favorite_misses_the_top3(finish: int | None, expected: int):
    samples = pd.DataFrame({"finish": [finish]}, index=[7])
    targets = OutOfTop3TargetBuilder().build(samples)
    assert targets[OUT_OF_TOP3].tolist() == [expected]
    assert targets.index.tolist() == [7]


def test_target_builder_names_the_label():
    assert OutOfTop3TargetBuilder().label_name == OUT_OF_TOP3


def test_training_data_holds_only_favorites(training_data: TrainingData):
    # 架空のシーズンは 10頭立てなので、人気馬は 1〜3番人気
    assert training_data.evaluation[POPULARITY].between(1, 3).all()
    assert list(training_data.features.columns) == list(CATALOG.names)
    assert training_data.features.index.equals(training_data.ids.index)


def test_training_targets_follow_the_final_finish(training_data: TrainingData):
    finish = training_data.evaluation[FINISH].astype("float64")
    assert (training_data.targets[OUT_OF_TOP3] == (~finish.between(1, 3)).astype(int)).all()
    # 競走中止（着順なし）の人気馬は、走ったが馬券にならなかったので 1
    is_stopped = finish.isna()
    assert is_stopped.any() and (training_data.targets.loc[is_stopped, OUT_OF_TOP3] == 1).all()


def test_training_data_has_the_popularity_features(training_data: TrainingData):
    assert training_data.features["人気順位"].between(1, 3).all()
    assert training_data.features["近5走の平均人気"].notna().any()
