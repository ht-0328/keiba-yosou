"""K. 重賞の傾向の計算（帯分けと、過去の開催で自分と同じ帯だった馬の成績の突き合わせ）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.feature import EntryRecords, WorkoutCoverage

from 共通.stakes import NO_PREV_KEY

from ..feature.condition_bands import ConditionBands
from ..feature.stakes_tendency_features import StakesTendencyFeatures
from ..feature.tendency_cut import EDITIONS, FAV1_PLACE_RATE, FAV123_PLACE_RATE, PLACE_RATE, RUNS, STATS, WIN_PAYBACK, cut_keyed

#: 対象の重賞と、重賞でないレース。
STAKES_RID, FLAT_RID = "2026010105010106", "2026010105010101"
#: 過去の開催（2つ）の rid。
PAST_RIDS = ("2025010405010106", "2024010605010106")


def _records(entries: pd.DataFrame, tendency: pd.DataFrame) -> EntryRecords:
    empty = pd.DataFrame()
    return EntryRecords(
        entries=entries, past_runs=empty, workouts=empty, workout_coverage=WorkoutCoverage.from_table(empty),
        jockey_days=empty, trainer_days=empty, sire_days=empty, damsire_days=empty,
        stakes_tendency=tendency,
    )


def _past_row(race_id: str, horse_id: str, finish: int, popularity: int, win_odds: float, prev_key: str,
              frame_no: int = 1, style: str = "逃げ", interval_days: float = 30, affiliation: str = "栗東",
              experience: int = 0, age: int = 4, sex: str = "牡", prev_finish: float = 1, prev_popularity: float = 1) -> dict:
    """過去の開催の1頭。払戻は 100円あたり（外れは 0）。"""
    return {
        "target_race_id": STAKES_RID, "is_target": False, "race_id": race_id, "stakes_no": "9001",
        "race_date": pd.Timestamp(race_id[:4] + "-01-05"), "horse_id": horse_id,
        "finish": finish, "popularity": popularity, "win_odds": win_odds, "frame_no": frame_no, "style": style,
        "interval_days": interval_days, "affiliation": affiliation, "same_race_places_before": experience, "age": age, "sex": sex,
        "prev_finish": prev_finish, "prev_popularity": prev_popularity,
        "win_payout": win_odds * 100 if finish == 1 else 0.0, "place_payout": 150.0 if finish <= 3 else 0.0, "prev_key": prev_key,
    }


def _target_row(horse_id: str, prev_key: str) -> dict:
    row = {key: None for key in _past_row(STAKES_RID, horse_id, 1, 1, 1.0, prev_key)}
    row.update({"target_race_id": STAKES_RID, "is_target": True, "race_id": STAKES_RID, "stakes_no": "9001",
                "race_date": pd.Timestamp("2026-01-05"), "horse_id": horse_id, "prev_key": prev_key})
    return row


def _tendency() -> pd.DataFrame:
    """過去2開催 × 3頭。前走が「重賞 0008」だった馬は 3頭中2頭が3着以内。1番人気は 2回とも3着以内。"""
    first, second = PAST_RIDS
    rows = [
        _past_row(first, "p1", 1, 1, 2.5, "重賞 0008", frame_no=1, style="逃げ", age=4),
        _past_row(first, "p2", 5, 3, 8.0, "重賞 0008", frame_no=4, style="差し", age=5, interval_days=70),
        _past_row(first, "p3", 2, 6, 15.0, "3勝クラス", frame_no=7, style="追込", age=3, sex="牝"),
        _past_row(second, "p4", 3, 1, 1.8, "重賞 0008", frame_no=2, style="先行", age=6),
        _past_row(second, "p5", 9, 2, 4.0, NO_PREV_KEY, frame_no=5, style="不明", age=4, affiliation="美浦",
                  interval_days=np.nan, prev_finish=np.nan, prev_popularity=np.nan),
        _past_row(second, "p6", 1, 8, 20.0, "3勝クラス", frame_no=8, style="差し", age=4, experience=1),
    ]
    rows += [_target_row("h1", "重賞 0008"), _target_row("h2", "3勝クラス")]
    return pd.DataFrame(rows)


def _entries(frame_no: object = 1, win_odds: object = 2.0) -> pd.DataFrame:
    """対象の重賞の2頭（h1 は前走が重賞 0008、h2 は前走が 3勝クラスで前走の記録なし）と、重賞でないレースの1頭。"""
    return pd.DataFrame([
        {"race_id": STAKES_RID, "horse_id": "h1", "grade_code": "C", "prev_finish": 1, "prev_popularity": 2, "frame_no": frame_no,
         "win_odds": win_odds, "style_before": "逃げ", "interval_days": 28, "affiliation": "栗東", "same_race_places_before": 0,
         "age": 4, "sex": "牡"},
        {"race_id": STAKES_RID, "horse_id": "h2", "grade_code": "C", "prev_finish": np.nan, "prev_popularity": np.nan, "frame_no": 8,
         "win_odds": 12.0, "style_before": None, "interval_days": np.nan, "affiliation": "美浦", "same_race_places_before": 1,
         "age": 3, "sex": "牝"},
        {"race_id": FLAT_RID, "horse_id": "h3", "grade_code": " ", "prev_finish": 2, "prev_popularity": 1, "frame_no": 3,
         "win_odds": 3.0, "style_before": "先行", "interval_days": 14, "affiliation": "栗東", "same_race_places_before": 0,
         "age": 4, "sex": "牡"},
    ])


def _name(key: str, stat: str) -> str:
    return cut_keyed(key).feature_name(stat)


def test_same_previous_race_counts_the_runners_of_that_race_only():
    """h1 の前走は重賞 0008。過去2開催で前走が重賞 0008 だった馬は3頭（p1・p2・p4）で、うち2頭が3着以内。単勝は p1 の 2.5倍だけ的中。"""
    features = StakesTendencyFeatures().build(_records(_entries(), _tendency()))
    assert features.loc[0, _name("prev_race", RUNS)] == 3
    assert features.loc[0, _name("prev_race", PLACE_RATE)] == pytest.approx(2 / 3)
    assert features.loc[0, _name("prev_race", WIN_PAYBACK)] == pytest.approx(250 / 300)
    # h2 の前走は 3勝クラス（p3・p6 の2頭。両方 3着以内）
    assert features.loc[1, _name("prev_race", RUNS)] == 2 and features.loc[1, _name("prev_race", PLACE_RATE)] == 1.0


def test_bands_follow_the_horse_s_own_condition():
    """枠（内 1〜3）、人気（オッズの順位）、脚質（前）、年齢、性別は、自分の帯の馬だけを数える。"""
    features = StakesTendencyFeatures().build(_records(_entries(), _tendency()))
    # h1 は1枠（内）。過去の内枠は p1・p4 の2頭で、両方 3着以内
    assert features.loc[0, _name("frame", RUNS)] == 2 and features.loc[0, _name("frame", PLACE_RATE)] == 1.0
    # h1 は 2.0倍で h2（12倍）より低いので 1番人気の帯。過去の1番人気は p1・p4（両方 3着以内）
    assert features.loc[0, _name("popularity", RUNS)] == 2 and features.loc[0, _name("popularity", PLACE_RATE)] == 1.0
    # h2 は 12倍 → 10〜20倍の帯。過去の 10〜20倍は p3 の1頭（2着）
    assert features.loc[1, _name("odds", RUNS)] == 1 and features.loc[1, _name("odds", PLACE_RATE)] == 1.0
    # 推定脚質が逃げ → 前。過去の前（逃げ・先行）は p1・p4
    assert features.loc[0, _name("style", RUNS)] == 2
    # h2 は推定脚質なし → 不明。過去の不明は p5 の1頭（9着）
    assert features.loc[1, _name("style", RUNS)] == 1 and features.loc[1, _name("style", PLACE_RATE)] == 0.0
    # 3歳の牝馬 h2: 過去の3歳は p3、牝馬も p3
    assert features.loc[1, _name("age", RUNS)] == 1 and features.loc[1, _name("sex", RUNS)] == 1
    # h2 は前走の記録なし → 前走の着順・人気・間隔は「前走なし」の帯。過去の「前走なし」は p5 の1頭だけ（9着）
    assert features.loc[1, _name("prev_finish", RUNS)] == 1 and features.loc[1, _name("prev_finish", PLACE_RATE)] == 0.0
    assert features.loc[1, _name("interval", RUNS)] == 1 and features.loc[1, _name("prev_popularity", RUNS)] == 1


def test_race_level_columns_count_the_past_editions_and_the_favorites():
    features = StakesTendencyFeatures().build(_records(_entries(), _tendency()))
    assert (features.loc[[0, 1], EDITIONS] == 2).all()
    assert features.loc[0, FAV1_PLACE_RATE] == 1.0  # p1（1着）・p4（3着）
    assert features.loc[0, FAV123_PLACE_RATE] == pytest.approx(2 / 4)  # p1・p2・p4・p5 のうち p1・p4


def test_unknown_bands_and_non_stakes_rows_are_missing():
    """木曜（枠・オッズ未定）は枠・オッズ・人気の切り口が欠損値。重賞でないレースの行は全部欠損値。"""
    features = StakesTendencyFeatures().build(_records(_entries(frame_no=np.nan, win_odds=np.nan), _tendency()))
    for key in ("frame", "odds", "popularity"):
        assert all(np.isnan(features.loc[0, _name(key, stat)]) for stat in STATS)
    assert features.loc[0, _name("prev_race", RUNS)] == 3  # 木曜でも前走のレースは分かる
    assert features.loc[2].isna().all()


def test_a_stakes_race_without_past_editions_has_zero_editions_and_missing_stats():
    tendency = _tendency()
    only_targets = tendency[tendency["is_target"].astype(bool)]
    features = StakesTendencyFeatures().build(_records(_entries(), only_targets))
    assert features.loc[0, EDITIONS] == 0 and np.isnan(features.loc[0, _name("prev_race", RUNS)])
    assert np.isnan(features.loc[2, EDITIONS])


def test_condition_bands_use_the_same_edges_for_both_sides():
    bands = ConditionBands()
    assert bands.odds(pd.Series([1.5, 3.0, 5.9, 10.0, 49.9, 50.0, np.nan])).tolist()[:6] == [
        "3倍未満", "3〜6倍", "3〜6倍", "10〜20倍", "20〜50倍", "50倍以上"]
    assert pd.isna(bands.odds(pd.Series([np.nan]))).all()
    assert bands.popularity(pd.Series([1, 2, 3, 4, 5, 6, 9, 10, 18])).tolist() == [
        "1番人気", "2〜3番人気", "2〜3番人気", "4〜5番人気", "4〜5番人気", "6〜9番人気", "6〜9番人気", "10番人気以下", "10番人気以下"]
    assert bands.frame(pd.Series([1, 3, 4, 5, 6, 8])).tolist() == ["内", "内", "中", "中", "外", "外"]
    assert bands.age(pd.Series([2, 3, 4, 5, 6, 9])).tolist() == ["2歳", "3歳", "4歳", "5歳", "6歳以上", "6歳以上"]
    assert bands.interval(pd.Series([62, 63, np.nan])).tolist() == ["休み明けでない", "休み明け", NO_PREV_KEY]
    assert bands.prev_finish(pd.Series([1, 2, 3, 4, 9, 10, np.nan])).tolist() == [
        "1着", "2〜3着", "2〜3着", "4〜9着", "4〜9着", "10着以下", NO_PREV_KEY]
