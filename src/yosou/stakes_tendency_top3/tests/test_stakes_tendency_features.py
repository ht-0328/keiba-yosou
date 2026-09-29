"""K. 重賞の傾向の計算（縮めたずれと、馬の側との掛け合わせ）。"""

from __future__ import annotations

import pandas as pd
import pytest

from yosou.shared.feature import EntryRecords, WorkoutCoverage

from ..feature.stakes_tendency_features import (
    EDITIONS,
    FAV123_GAP,
    FRONT_GAP,
    FRONT_GAP_SELF,
    INNER_GAP_SELF,
    REST_GAP_SELF,
    SHRINK_FAV123,
    SHRINK_FRONT,
    StakesTendencyFeatures,
)


def _records(entries: pd.DataFrame, tendency: pd.DataFrame) -> EntryRecords:
    empty = pd.DataFrame()
    return EntryRecords(
        entries=entries, past_runs=empty, workouts=empty, workout_coverage=WorkoutCoverage.from_table(empty),
        jockey_days=empty, trainer_days=empty, sire_days=empty, damsire_days=empty,
        stakes_tendency=tendency,
    )


def _tendency_row(**over: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "race_id": "2026010105010106", "stakes_no": "9001", "grade": "C", "editions": 4,
        "fav1_n": 4, "fav1_hits": 3, "fav123_n": 12, "fav123_hits": 9,
        "front_n": 12, "front_hits": 6, "front_exp": 3.0,
        "inner_n": 12, "inner_hits": 3, "inner_exp": 3.0,
        "rest_n": 10, "rest_hits": 5, "west_n": 10, "west_hits": 5, "repeat_n": 4, "repeat_hits": 2,
        "base_fav1": 0.6, "base_fav123": 0.5, "base_rest": 0.3, "base_west": 0.3, "base_repeat": 0.3,
        "base_front_excess": 0.05, "base_inner_excess": 0.0,
    }
    row.update(over)
    return pd.DataFrame([row])


def _entries(**over: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "race_id": "2026010105010106", "style_before": "逃げ", "frame_no": 1,
        "interval_days": 70, "affiliation": "栗東", "same_race_places_before": 1,
    }
    row.update(over)
    return pd.DataFrame([row])


def test_gap_shrinks_toward_zero_by_sample_size():
    """上位人気のずれ = n/(n+k) × (過去の率 − 基準)。n=12・k=24 なら、ずれを 1/3 だけ信じる。"""
    features = StakesTendencyFeatures().build(_records(_entries(), _tendency_row()))
    expected = 12 / (12 + SHRINK_FAV123) * (9 / 12 - 0.5)
    assert features[FAV123_GAP].iloc[0] == pytest.approx(expected)
    assert features[EDITIONS].iloc[0] == 4


def test_front_gap_compares_excess_rates():
    """前のずれは、超過複勝率（3着内率 − 3÷頭数）どうしの差。頭数の違いに引きずられない。"""
    features = StakesTendencyFeatures().build(_records(_entries(), _tendency_row()))
    race_excess = (6 - 3.0) / 12
    expected = 12 / (12 + SHRINK_FRONT) * (race_excess - 0.05)
    assert features[FRONT_GAP].iloc[0] == pytest.approx(expected)
    assert features[FRONT_GAP_SELF].iloc[0] == pytest.approx(expected)  # 推定脚質が逃げ → そのまま


def test_interactions_are_zero_when_the_horse_does_not_match():
    """差し・外枠・休み明けでない馬では、掛け合わせの特徴量は 0。"""
    entries = _entries(style_before="差し", frame_no=8, interval_days=14)
    features = StakesTendencyFeatures().build(_records(entries, _tendency_row()))
    assert features[FRONT_GAP_SELF].iloc[0] == 0.0
    assert features[INNER_GAP_SELF].iloc[0] == 0.0
    assert features[REST_GAP_SELF].iloc[0] == 0.0


def test_missing_history_and_base_fall_back_to_zero():
    """過去の開催が無い（n=0）・基準が無い（NaN）ときは、ずれ 0（基準どおり）として扱う。"""
    tendency = _tendency_row(fav123_n=0, fav123_hits=0, base_front_excess=float("nan"))
    features = StakesTendencyFeatures().build(_records(_entries(), tendency))
    assert features[FAV123_GAP].iloc[0] == 0.0
    assert features[FRONT_GAP].iloc[0] == 0.0


def test_non_stakes_races_get_all_zeros():
    """重賞でないレース（傾向の行が無い）は、全部 0。"""
    entries = _entries(race_id="2026010105010101")
    features = StakesTendencyFeatures().build(_records(entries, _tendency_row()))
    assert (features.iloc[0] == 0.0).all()
