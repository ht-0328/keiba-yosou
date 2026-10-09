"""まとまり R（距離の変更の傾向）の数え方と読み方。合成DB と手で作った記録だけを使う。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from 共通 import facts
from 合成DB import synth

from ..dataset import DistanceChangeRecordsLoader
from ..feature import DISTANCE_CHANGE_FEATURES
from ..feature.history import DISTANCE_CHANGE_NAMES, DistanceChangeTendency
from ..feature.history.distance_change_tendency import SHRINK_COURSE, SHRINK_STAKES
from ..repository import TargetScope

GAP, COURSE_STARTS, WIN_EXCESS, TOP3_EXCESS, LONGSHOT_EXCESS, STAKES_STARTS, STAKES_EXCESS = DISTANCE_CHANGE_NAMES


def _past_race() -> pd.DataFrame:
    """2024-04-06 の東京 芝・左 1600m の重賞（特別競走番号 0001）。4頭とも単勝 4.0倍（勝率 0.25・3着以内率 0.75 の期待）。
    短縮の馬が1着、同じの2頭が2・3着、延長の馬（6番人気）が4着。"""
    rows = [("短縮", 1, 1), ("同じ", 2, 2), ("同じ", 3, 3), ("延長", 4, 6)]
    return pd.DataFrame([{
        "race_id": "R1", "race_date": pd.Timestamp("2024-04-06"), "venue": "東京", "course": "芝・左", "distance_m": 1600,
        "distance_change": change, "popularity": popularity, "win_odds": 4.0, "finish": finish, "stakes_no": "0001",
    } for change, finish, popularity in rows])


def _target(day: str, change: str, distance: int = 1600, stakes_no: str | None = "0001") -> dict:
    return {"race_date": pd.Timestamp(day), "venue": "東京", "course": "芝・左", "distance_m": distance,
            "distance_change": change, "prev_distance_m": 1800 if change == "短縮" else 1400, "stakes_no": stakes_no}


def test_the_seven_features_are_numbers_in_group_r_known_from_thursday():
    assert [feature.name for feature in DISTANCE_CHANGE_FEATURES] == list(DISTANCE_CHANGE_NAMES)
    assert len(DISTANCE_CHANGE_NAMES) == 7
    assert all(feature.group == "R" and feature.known_from.value == "thursday" for feature in DISTANCE_CHANGE_FEATURES)


def test_the_tendency_counts_horses_with_the_same_change_at_the_same_course_before_the_race_day():
    targets = pd.DataFrame([
        _target("2024-04-13", "短縮"),                      # 前の週の短縮の馬は1着（期待より +0.75 勝ち、+0.25 3着以内）
        _target("2024-04-13", "延長"),                      # 前の週の延長の馬は6番人気で4着
        _target("2024-04-06", "短縮"),                      # 同じ日のレースは数えない
        _target("2024-04-13", "短縮", distance=1800),       # 別の距離は数えない
        _target("2024-04-13", "短縮", stakes_no=None),      # 重賞でなければ重賞の列は欠損値
    ])
    table = DistanceChangeTendency().of(targets, _past_race())
    shorter, longer, same_day, other_distance, not_stakes = (table.iloc[row] for row in range(5))
    assert shorter[GAP] == -200 and longer[GAP] == 200
    assert shorter[COURSE_STARTS] == 1
    assert shorter[WIN_EXCESS] == pytest.approx((1 - 0.25) / (1 + SHRINK_COURSE))
    assert shorter[TOP3_EXCESS] == pytest.approx((1 - 0.75) / (1 + SHRINK_COURSE))
    assert shorter[LONGSHOT_EXCESS] == 0, "短縮の穴馬は前の週にいない"
    assert longer[LONGSHOT_EXCESS] == pytest.approx((0 - 0.75) / (1 + SHRINK_COURSE))
    assert longer[STAKES_STARTS] == 1 and longer[STAKES_EXCESS] == pytest.approx((0 - 0.75) / (1 + SHRINK_STAKES))
    assert same_day[COURSE_STARTS] == 0 and same_day[WIN_EXCESS] == 0
    assert other_distance[COURSE_STARTS] == 0
    assert pd.isna(not_stakes[STAKES_STARTS]) and pd.isna(not_stakes[STAKES_EXCESS]) and not_stakes[COURSE_STARTS] == 1


def test_the_loader_reads_the_targets_and_the_past_runs_from_the_facts(tmp_path: Path):
    """同じ馬が同じコースを2週続けて走った合成DB。2週目は5頭が「同じ」距離で、1週目の馬はみな前走なしなので、同じ変更の出走は 0。
    1週目に出走取消だった馬（馬番6）は、2週目も前走なしで距離の差は欠損値。"""
    sample = synth.simple_race(day="20240406").extend(synth.simple_race(day="20240413"))
    con = duckdb.connect(str(synth.build_db(tmp_path / "distance.duckdb", sample)), read_only=True)
    facts.ensure_facts(con)
    table = DistanceChangeRecordsLoader(con, pd.Timestamp("2011-01-01").date()).read(
        TargetScope.since(pd.Timestamp("2024-01-01").date()))
    assert list(table.columns) == ["race_id", "horse_id", *DISTANCE_CHANGE_NAMES]
    second = table[table["race_id"].str.startswith("20240413")]
    assert second[GAP].tolist()[:5] == [0, 0, 0, 0, 0] and pd.isna(second[GAP].iloc[5])
    assert second[COURSE_STARTS].tolist() == [0, 0, 0, 0, 0, 5], "前走なしの馬は、1週目の前走なしの5頭を数える"
    first = table[table["race_id"].str.startswith("20240406")]
    assert first[GAP].isna().all(), "1週目は前走なし"

