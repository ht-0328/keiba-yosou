"""トラックバイアスの式（傾き・過去の傾き・当日の傾き・使う傾き・補正・判定）。DB を使わず、手で作った表で確かめる。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from yosou.shared.feature import PredictionTiming

from .. import names
from ..bias_correction import BiasCorrection
from ..bias_judge import BiasJudge
from ..day_slopes import DaySlopes
from ..positions import Positions
from ..prior_slope_table_builder import POOL_WEIGHT, PriorSlopeTableBuilder
from ..race_slopes import RaceSlopes, meeting_day_of
from ..used_slopes import PRIOR_WEIGHT, UsedSlopes
from ..yearly_bias import YearlyBias


def _runs(race_id: str, day: str, race_no: int, finishes: list[int], odds: list[float], corners: list[int],
          condition: str = "1", venue: str = "06", track: str = "17") -> pd.DataFrame:
    size = len(finishes)
    return pd.DataFrame({
        names.RACE_ID: race_id, names.RACE_DATE: pd.Timestamp(day), names.VENUE_CODE: venue, names.SURFACE: "芝", names.TRACK_CODE: track,
        names.CONDITION_CODE: condition, names.RACE_NO: race_no, "field_size": size, "horse_id": [f"{race_id}h{i}" for i in range(size)],
        "horse_no": list(range(1, size + 1)), "corner4": corners, "finish": finishes, "win_odds": odds,
    })


def test_内らしさと前らしさは_最内と先頭が正0_5で大外と最後方が負0_5():
    positions = Positions()
    inner = positions.innerness(pd.Series([1, 2, 16, np.nan]), pd.Series([16, 16, 16, 16]))
    assert inner.round(3).tolist()[:3] == [0.5, 0.433, -0.5] and np.isnan(inner[3])
    assert np.isnan(positions.innerness(pd.Series([1]), pd.Series([1]))[0])   # 1頭立ては欠損値
    assert positions.frontness_of_rank(pd.Series([1, 16]), pd.Series([16, 16])).tolist() == [0.5, -0.5]
    assert positions.frontness_of_position(pd.Series([0.0, 1.0, 0.25])).tolist() == [0.5, -0.5, 0.25]


def test_傾きは_市場の見立てより内と前が来ていれば正で_4角の無いレースは前の傾きが欠損値():
    # 4頭立て。オッズは同じ（市場の見立ては均等）で、内の2頭が3着以内なら内の傾きは正。前の2頭（4角 1・2）が内の2頭なら前の傾きも正
    inner = _runs("r1", "2024-04-13", 1, [1, 2, 3, 4], [4.0, 4.0, 4.0, 4.0], [1, 2, 3, 4])
    none = _runs("r2", "2024-04-13", 2, [4, 3, 2, 1], [4.0, 4.0, 4.0, 4.0], [np.nan] * 4)
    slopes = RaceSlopes().of(pd.concat([inner, none], ignore_index=True))
    assert slopes[names.RACE_ID].tolist() == ["r1", "r2"]
    first, second = slopes.iloc[0], slopes.iloc[1]
    assert first[names.INNER_SLOPE] > 0 and first[names.FRONT_SLOPE] > 0
    assert second[names.INNER_SLOPE] < 0 and np.isnan(second[names.FRONT_SLOPE])
    assert meeting_day_of(pd.Series(["2026100405050811"])).tolist() == [8.0]


def test_過去の傾きの表は_マスの平均を同じ馬場の平均に寄せ_無いマスは馬場の値か0():
    rows = [_runs(f"r{i}", f"2023-0{1 + i % 9}-0{1 + i % 9}", 1, [1, 2, 3, 4], [4.0] * 4, [1, 2, 3, 4]) for i in range(10)]
    slopes = RaceSlopes().of(pd.concat(rows, ignore_index=True))
    slopes[names.MEETING_DAY] = [1.0] * 5 + [2.0] * 5
    table = PriorSlopeTableBuilder().build(slopes)
    course_mean = slopes[names.INNER_SLOPE].mean()
    cell_mean = slopes[names.INNER_SLOPE][:5].mean()
    expected = (5 * cell_mean + POOL_WEIGHT * course_mean) / (5 + POOL_WEIGHT)
    looked = table.lookup(pd.DataFrame({names.VENUE_CODE: ["06", "06", "05"], names.SURFACE: "芝", names.TRACK_CODE: "17",
                                        names.MEETING_DAY: [1.0, 7.0, 1.0], names.CONDITION_CODE: "1"}, index=[3, 4, 5]))
    assert abs(looked.loc[3, names.PRIOR_INNER] - expected) < 1e-9
    assert abs(looked.loc[4, names.PRIOR_INNER] - course_mean) < 1e-9   # 無いマスは同じ馬場の値
    assert looked.loc[5, names.PRIOR_INNER] == 0.0 and list(looked.index) == [3, 4, 5]   # 知らない馬場は 0
    # いつもの傾き（同じ馬場の全期間の平均）も添える
    assert abs(looked.loc[3, names.COURSE_INNER] - course_mean) < 1e-9 and looked.loc[5, names.COURSE_FRONT] == 0.0
    # before を渡すと、その日より前のレースだけ
    assert PriorSlopeTableBuilder().build(slopes, before=date(2023, 1, 1)).as_of is None
    assert PriorSlopeTableBuilder().build(slopes, before=date(2023, 3, 1)).as_of == date(2023, 2, 2)


def _slopes_two_days() -> pd.DataFrame:
    rows = [
        _runs("a1", "2024-04-13", 1, [1, 2, 3, 4], [4.0] * 4, [1, 2, 3, 4]),             # 前の日の1R（内が来た）
        _runs("a2", "2024-04-13", 2, [4, 3, 2, 1], [4.0] * 4, [4, 3, 2, 1]),             # 前の日の2R（外が来た）
        _runs("b1", "2024-04-14", 1, [1, 2, 3, 4], [4.0] * 4, [1, 2, 3, 4]),             # 当日の1R（内が来た）
        _runs("b2", "2024-04-14", 2, [1, 2, 3, 4], [4.0] * 4, [1, 2, 3, 4], condition="2"),   # 当日の2R（馬場が変わった）
        _runs("b3", "2024-04-14", 3, [1, 2, 3, 4], [4.0] * 4, [1, 2, 3, 4], condition="2"),   # 当日の3R（対象）
        _runs("c1", "2024-04-14", 1, [1, 2, 3, 4], [4.0] * 4, [1, 2, 3, 4], venue="05"),      # 別の競馬場（数えない）
    ]
    return RaceSlopes().of(pd.concat(rows, ignore_index=True))


def test_当日の傾きは_先に終わったレースと前の日のレースを重みで混ぜ_前日は前の日だけ_木曜は数えない():
    slopes = _slopes_two_days()
    target = slopes[slopes[names.RACE_ID] == "b3"]
    by_id = slopes.set_index(names.RACE_ID)[names.INNER_SLOPE]
    race_day = DaySlopes().of(target, slopes, PredictionTiming.RACE_DAY)
    # 当日: b1 は馬場が違うので 0.5、b2 は 1、前の日の a1・a2 は 0.5 ずつ → レース数 2.5
    assert race_day[names.RACES].tolist() == [2.5]
    expected = (0.5 * by_id["b1"] + 1.0 * by_id["b2"] + 0.5 * by_id["a1"] + 0.5 * by_id["a2"]) / 2.5
    assert abs(race_day[names.INNER_SLOPE].iloc[0] - expected) < 1e-9
    day_before = DaySlopes().of(target, slopes, PredictionTiming.DAY_BEFORE)
    assert day_before[names.RACES].tolist() == [1.0] and abs(day_before[names.INNER_SLOPE].iloc[0] - (by_id["a1"] + by_id["a2"]) / 2) < 1e-9
    thursday = DaySlopes().of(target, slopes, PredictionTiming.THURSDAY)
    assert thursday[names.RACES].tolist() == [0.0] and np.isnan(thursday[names.INNER_SLOPE].iloc[0])
    assert list(race_day.index) == list(target.index)
    # 終わった日: 対象が b2 なら、その日のほかの全部のレース（b1 は馬場が違うので 0.5、後の b3 も 1）と前の日（0.5 × 2）→ 2.5
    whole = DaySlopes().of_finished_day(slopes[slopes[names.RACE_ID] == "b2"], slopes)
    assert whole[names.RACES].tolist() == [2.5]
    expected = (0.5 * by_id["b1"] + 1.0 * by_id["b3"] + 0.5 * by_id["a1"] + 0.5 * by_id["a2"]) / 2.5
    assert abs(whole[names.INNER_SLOPE].iloc[0] - expected) < 1e-9


def test_使う傾きは_当日と過去をレース数と重みkで混ぜ_当日が無ければ過去のまま():
    day = pd.DataFrame({names.INNER_SLOPE: [0.12, np.nan], names.FRONT_SLOPE: [np.nan, 0.1], names.RACES: [3.0, 0.0]}, index=[7, 8])
    prior = pd.DataFrame({names.PRIOR_INNER: [0.04, 0.02], names.PRIOR_FRONT: [0.01, 0.03]}, index=[7, 8])
    used = UsedSlopes().of(day, prior)
    assert abs(used.loc[7, names.USED_INNER] - (3 * 0.12 + PRIOR_WEIGHT * 0.04) / (3 + PRIOR_WEIGHT)) < 1e-9
    assert used.loc[7, names.USED_FRONT] == 0.01 and used.loc[8, names.USED_INNER] == 0.02 and used.loc[8, names.USED_FRONT] == 0.03


def test_補正は_使う傾きと内らしさの積と_使う傾きと予想の前らしさの積の和で_判定は線で分ける():
    entries = pd.DataFrame({names.RACE_ID: ["r", "r", "r"], "horse_id": ["x", "y", "z"], "horse_no": [2, 16, 9], "field_size": 16,
                            "corner4_pred": [0.0, 1.0, np.nan]}, index=[1, 2, 3])
    # いつもの前の傾きが +0.2 なら、使う前の傾き +0.25 のうち、その日の分は +0.05
    used = pd.DataFrame({names.USED_INNER: [0.074], names.USED_FRONT: [0.25], names.COURSE_INNER: [0.0], names.COURSE_FRONT: [0.2]}, index=["r"])
    table = BiasCorrection().of(entries, used)
    assert abs(table.loc[1, names.INNER_PART] - 0.074 * (0.5 - 1 / 15)) < 1e-9 and abs(table.loc[1, names.FRONT_PART] - 0.025) < 1e-9
    assert abs(table.loc[1, names.CORRECTION] - (0.074 * (0.5 - 1 / 15) + 0.025)) < 1e-9
    assert table[names.FRONT_SLOPE_FEATURE].tolist() == [0.25] * 3   # 使う傾きそのものは、いつもの分を引かずに残す
    # いつもの傾きの列が無ければ 0 とみなす
    plain = BiasCorrection().of(entries, used[[names.USED_INNER, names.USED_FRONT]])
    assert abs(plain.loc[1, names.FRONT_PART] - 0.125) < 1e-9
    assert table.loc[2, names.CORRECTION] < 0 and np.isnan(table.loc[3, names.CORRECTION]) and not np.isnan(table.loc[3, names.INNER_PART])
    assert table[names.INNER_SLOPE_FEATURE].tolist() == [0.074] * 3 and list(table.index) == [1, 2, 3]
    verdict = BiasJudge().of(pd.Series([0.03, -0.02, 0.01, np.nan]))
    assert verdict.tolist() == [names.WITH_BIAS, names.AGAINST_BIAS, names.NEUTRAL, names.NEUTRAL]


def test_年ごとの補正は_その年より前の過去の傾きと先に終わったレースで付け_材料に無い行は欠損値():
    slopes = _slopes_two_days()
    runs = pd.concat([_runs("b3", "2024-04-14", 3, [1, 2, 3, 4], [4.0] * 4, [1, 2, 3, 4], condition="2")], ignore_index=True)
    forecasts = pd.DataFrame({"race_id": ["b3", "b3", "zz"], "horse_id": ["b3h0", "b3h3", "q"], "corner4_pred": [0.0, 1.0, 0.5]}, index=[10, 11, 12])
    table = YearlyBias().of(forecasts, runs, slopes, PredictionTiming.RACE_DAY)
    assert list(table.index) == [10, 11, 12] and table.loc[10, names.CORRECTION] > 0 > table.loc[11, names.CORRECTION]
    assert np.isnan(table.loc[12, names.CORRECTION]) and pd.isna(table.loc[12, "race_date"])
    # 過去の傾きは 2024年より前のレースが無いので 0 → 使う傾きは当日の傾き × 2.5 ÷ 6.5
    day = DaySlopes().of(slopes[slopes[names.RACE_ID] == "b3"], slopes, PredictionTiming.RACE_DAY)
    expected = day[names.INNER_SLOPE].iloc[0] * 2.5 / (2.5 + PRIOR_WEIGHT)
    assert abs(table.loc[10, names.INNER_SLOPE_FEATURE] - expected) < 1e-9


@pytest.mark.parametrize("timing", [PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY])
def test_終わったレースが無くても_当日の傾きは欠損値でレース数0(timing: PredictionTiming):
    target = _slopes_two_days().iloc[[0]]
    empty = DaySlopes().of(target, target.iloc[0:0], timing)
    assert empty[names.RACES].tolist() == [0.0] and np.isnan(empty[names.INNER_SLOPE].iloc[0])
