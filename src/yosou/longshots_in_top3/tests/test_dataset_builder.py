"""穴馬の選び方と区分（設計書 06 の図1・08 の 3）、目的変数の付け方（設計書 10）、区分での絞り込み。

行の選び方と区分は DB を使わず、手で作った出走の行で確かめる。最後に、合成DB から作った学習データで、
同じ決まりが通しでも守られていることを確かめる。
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import TOP3, WIN, TrainingData
from yosou.shared.dataset.column_names import FINISH, POPULARITY

from ..dataset import (
    IS_LONGSHOT,
    LONGSHOT_ZONE,
    LongshotRule,
    LongshotSelector,
    LongshotZone,
    LongshotZoneFilter,
)
from ..feature import CATALOG

RACE = "2024060105010101"
RACE_DAY = date(2024, 6, 1)
TRAIN_FIRST_DAY = date(2024, 1, 1)
MID, BIG = LongshotZone.MID.label, LongshotZone.BIG.label


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


def _selector() -> LongshotSelector:
    return LongshotSelector(LongshotRule())


@pytest.mark.parametrize(("field_size", "first"), [(7, 4), (13, 4), (14, 6), (18, 6)])
def test_longshot_range_starts_right_after_the_favorites(field_size: int, first: int):
    # 人気馬（13頭以下 1〜3番、14頭以上 1〜5番）の裏返し。いちばん下は最下位
    assert LongshotRule().popularity_range(field_size) == (first, field_size)


@pytest.mark.parametrize(("popularity", "field_size", "expected"), [
    (3, 13, False), (4, 13, True), (13, 13, True), (5, 14, False), (6, 14, True), (18, 18, True),
])
def test_longshot_judgement_at_the_boundary(popularity: int, field_size: int, expected: bool):
    assert LongshotRule().is_longshot(popularity, field_size) is expected


@pytest.mark.parametrize(("popularity", "field_size", "zone"), [
    (3, 13, None), (4, 13, LongshotZone.MID), (6, 13, LongshotZone.MID), (7, 13, LongshotZone.BIG),
    (13, 13, LongshotZone.BIG),
    (5, 14, None), (6, 14, LongshotZone.MID), (9, 14, LongshotZone.MID), (10, 14, LongshotZone.BIG),
    (18, 18, LongshotZone.BIG),
])
def test_zone_at_the_boundary(popularity: int, field_size: int, zone: LongshotZone | None):
    assert LongshotRule().zone_of(popularity, field_size) is zone


def test_missing_popularity_is_not_a_longshot():
    # 人気が分からない馬は、穴馬にしない（4番人気以下かどうかを決められないため）
    assert LongshotRule().is_longshot(None, 16) is False
    assert LongshotRule().is_longshot(float("nan"), 16) is False
    assert LongshotRule().zone_of(None, 16) is None


def test_zones_of_labels_every_runner_of_a_large_field():
    entries = _field(16)
    field_size = pd.Series([16] * 16)
    zones = LongshotRule().zones_of(entries["popularity"], field_size)
    assert zones.tolist() == [None] * 5 + [MID] * 4 + [BIG] * 7


def test_zone_parse_reads_the_labels_and_rejects_others():
    assert LongshotZone.parse("中穴") is LongshotZone.MID and LongshotZone.parse(" 大穴 ") is LongshotZone.BIG
    with pytest.raises(ValueError, match="中穴 / 大穴"):
        LongshotZone.parse("超大穴")


def test_training_samples_keep_every_flat_runner_with_the_longshot_columns():
    # レース内順位を全出走馬から計算するので、穴馬でない行もいったんは残す（設計書 08 の 3）
    entries = _field(14)
    samples = _selector().training_samples(entries, TRAIN_FIRST_DAY)
    assert len(samples) == 14
    assert samples[IS_LONGSHOT].tolist() == [False] * 5 + [True] * 9
    assert samples[LONGSHOT_ZONE].tolist() == [None] * 5 + [MID] * 4 + [BIG] * 5


def test_training_samples_drop_jumps_scratches_and_the_warmup_period():
    entries = pd.DataFrame([
        _runner(4),
        _runner(5, race_id="2024060105010102", surface="障害"),
        _runner(6, ran=False),
        _runner(7, race_id="2023060105010101", day=date(2023, 6, 1)),
    ])
    samples = _selector().training_samples(entries, TRAIN_FIRST_DAY)
    assert samples["popularity"].tolist() == [4]


def test_keep_samples_leaves_only_the_longshots():
    selector = _selector()
    samples = selector.training_samples(_field(10), TRAIN_FIRST_DAY)
    kept = selector.keep_samples(samples)
    assert kept["popularity"].tolist() == [4, 5, 6, 7, 8, 9, 10]
    assert kept.index.tolist() == [3, 4, 5, 6, 7, 8, 9]
    assert kept[LONGSHOT_ZONE].tolist() == [MID] * 3 + [BIG] * 4


def test_field_size_counts_the_horses_that_ran():
    # 16頭登録でも、2頭が取消なら 14頭立て。14頭以上なので 6番人気以下が穴馬になる
    entries = pd.concat([_field(14), pd.DataFrame([_runner(15, ran=False), _runner(16, ran=False)])])
    samples = _selector().training_samples(entries.reset_index(drop=True), TRAIN_FIRST_DAY)
    assert samples[IS_LONGSHOT].sum() == 9


def test_prediction_stops_when_no_popularity_is_known():
    # 確定前のレースは、元DB の単勝人気が空。利用者に --pops で渡してもらう
    entries = pd.DataFrame([_runner(None) for _ in range(10)])
    with pytest.raises(ValueError, match="--pops"):
        _selector().prediction_runners(entries, RACE)


def test_prediction_stops_when_one_popularity_is_missing():
    # 穴馬は出走馬の大半なので、1頭でも人気が分からなければ黙って落とさずに止める（設計書 06 の図2）
    entries = pd.concat([_field(9), pd.DataFrame([_runner(None)])]).reset_index(drop=True)
    with pytest.raises(ValueError, match="1頭います.*--pops"):
        _selector().prediction_runners(entries, RACE)


def test_prediction_stops_when_no_longshot_runs():
    # 3頭立て（1〜3番人気）には穴馬がいない
    with pytest.raises(LookupError, match="穴馬がいません"):
        _selector().prediction_runners(_field(3), RACE)


def test_prediction_stops_for_jump_races_and_empty_fields():
    with pytest.raises(ValueError, match="障害"):
        _selector().prediction_runners(_field(10, surface="障害"), RACE)
    with pytest.raises(LookupError, match="出走する馬がいません"):
        _selector().prediction_runners(_field(10, ran=False), RACE)


def test_prediction_runners_carry_the_zone():
    runners = _selector().prediction_runners(_field(16), RACE)
    assert runners[LONGSHOT_ZONE].tolist() == [None] * 5 + [MID] * 4 + [BIG] * 7


def _prediction(zones: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"馬番": range(1, len(zones) + 1), LONGSHOT_ZONE: zones})


def test_zone_filter_keeps_only_the_zone_or_everything():
    prediction = _prediction([MID, MID, BIG])
    assert LongshotZoneFilter().apply(prediction, None) is prediction
    assert LongshotZoneFilter().apply(prediction, LongshotZone.BIG)["馬番"].tolist() == [3]
    assert LongshotZoneFilter().apply(prediction, LongshotZone.MID)["馬番"].tolist() == [1, 2]


def test_zone_filter_stops_when_the_zone_is_empty():
    with pytest.raises(LookupError, match="大穴の穴馬がいません"):
        LongshotZoneFilter().apply(_prediction([MID, MID]), LongshotZone.BIG)


def test_training_data_holds_only_longshots(training_data: TrainingData):
    # 架空のシーズンは 10頭立て（取消があれば 9頭）なので、穴馬は 4番人気以下
    assert training_data.evaluation[POPULARITY].between(4, 10).all()
    assert list(training_data.features.columns) == list(CATALOG.names)
    assert training_data.features.index.equals(training_data.ids.index)


def test_training_data_keeps_the_zone_for_evaluation(training_data: TrainingData):
    # 区分は特徴量ではなく、評価用の列として残る（設計書 08 の 2）
    assert LONGSHOT_ZONE not in training_data.features.columns
    zones = training_data.evaluation[LONGSHOT_ZONE]
    is_mid = training_data.evaluation[POPULARITY].between(4, 6)
    assert (zones[is_mid] == MID).all() and (zones[~is_mid] == BIG).all()


def test_training_targets_follow_the_final_finish(training_data: TrainingData):
    finish = training_data.evaluation[FINISH].astype("float64")
    assert (training_data.targets[TOP3] == finish.between(1, 3).astype(int)).all()
    assert (training_data.targets[WIN] == (finish == 1).astype(int)).all()
    # 競走中止（着順なし）の穴馬は、走ったが馬券にならなかったので 0
    is_stopped = finish.isna()
    assert is_stopped.any() and (training_data.targets.loc[is_stopped, TOP3] == 0).all()
    assert training_data.label_name == TOP3


def test_training_data_has_the_popularity_features(training_data: TrainingData):
    assert training_data.features["人気順位"].between(4, 10).all()
    assert training_data.features["近5走の平均人気"].notna().any()
    assert np.isfinite(training_data.features["出走頭数"]).all()
