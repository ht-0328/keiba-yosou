"""研究「全レース全券種の買い方」の部品のテスト。値は架空。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from yosou.shared.betting import TicketType  # noqa: E402

from 全レース全券種の買い方.analysis.day_table import HIT_RACES, PAYOUT, POINTS, RACES, DayTable  # noqa: E402
from 全レース全券種の買い方.analysis.formation import DOUBLE_AXIS, FLOW, Formation, candidates  # noqa: E402
from 全レース全券種の買い方.analysis.formation_mask import FormationMask  # noqa: E402
from 全レース全券種の買い方.analysis.grades_table import GradesTable  # noqa: E402
from 全レース全券種の買い方.analysis.half_year_folds import half_year_folds  # noqa: E402
from 全レース全券種の買い方.analysis.horse_slots import HorseSlots  # noqa: E402
from 全レース全券種の買い方.analysis.recovery_bootstrap import RecoveryBootstrap  # noqa: E402
from 全レース全券種の買い方.analysis.ticket_picker import TicketPicker  # noqa: E402
from 全レース全券種の買い方.analysis.upset_walk_forward import UpsetWalkForward  # noqa: E402


def _marked() -> pd.DataFrame:
    """1レース 6頭。◎4（確率 0.3）・○1（0.6）・▲2（0.5）・△3（0.4）・消5（0.45）・－6（0.2）。"""
    return pd.DataFrame({
        "race_id": "R", "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半",
        "horse_no": [1, 2, 3, 4, 5, 6], "mark": ["○", "▲", "△", "◎", "消", "－"], "probability": [0.6, 0.5, 0.4, 0.3, 0.45, 0.2],
        "win_probability": [0.3, 0.2, 0.1, 0.3, 0.2, 0.05], "win_value": [0.9, 0.8, 0.7, 0.9, 0.8, 0.6], "win_odds": [3.0, 4.0, 7.0, 3.0, 4.0, 12.0],
    })


def test_半年の区切りは印の成績と同じ名前で_検証は直前の半年() -> None:
    folds = half_year_folds(2015, 2016)
    assert [fold.name for fold in folds] == ["2015年前半", "2015年後半", "2016年"]
    assert (folds[0].first_day, folds[0].next_first_day, folds[0].valid_first_day) == (date(2015, 1, 1), date(2015, 7, 1), date(2014, 7, 1))
    assert (folds[2].first_day, folds[2].next_first_day, folds[2].valid_first_day) == (date(2016, 1, 1), date(2017, 1, 1), date(2015, 7, 1))


def test_配当率は4券種の中荒れ以上の確率の平均() -> None:
    predictions = pd.DataFrame({"race_id": ["R"] * 4, "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半",
                                "券種": ["単勝", "馬連", "3連複", "3連単"], "中荒れ以上の確率": [0.4, 0.5, 0.6, 0.7]})
    rates = UpsetWalkForward.payout_rates(predictions)
    assert rates.loc[0, "payout_rate"] == pytest.approx(0.55) and rates.loc[0, "3連単"] == pytest.approx(0.7)


def test_馬の位置は二重丸が0でほかは確率の順_消は無し() -> None:
    slots = HorseSlots().build(_marked()).set_index("horse_no")["pos"]
    assert slots[4] == 0 and slots[1] == 1 and slots[2] == 2 and slots[3] == 3 and slots[6] == 4 and np.isnan(slots[5])
    counts = HorseSlots().partner_counts(_marked()).set_index("race_id")
    assert counts.loc["R", "n50"] == 2 and counts.loc["R", "n25"] == 3   # ◎（0.3）と消（0.45）は数えない


def test_等級の表は二重丸ランクと配当率の等級をセルにする() -> None:
    rates = pd.DataFrame({"race_id": ["R"], "payout_rate": [0.8]})
    grades = GradesTable().build(_marked(), rates)
    assert grades.loc[0, ["hit_rate", "rank", "payout_grade", "cell"]].tolist() == [0.3, "A", "S", "A/S"] and grades.loc[0, "rank_score"] == pytest.approx(0.2)
    assert GradesTable().build(_marked(), None).loc[0, "cell"] == "A/－"
    low = _marked().assign(win_odds=[3.0, 4.0, 7.0, 1.8, 4.0, 12.0])
    assert GradesTable().build(low, rates).loc[0, ["odds_band", "cell"]].tolist() == ["2倍以下", "A/2倍以下"]
    assert GradesTable(split_low_odds=False).build(low, rates).loc[0, "cell"] == "A/S"


def test_型の候補は2頭以下が36で3頭の券種が72() -> None:
    assert len(candidates(TicketType.QUINELLA)) == 90 and len(candidates(TicketType.TRIFECTA)) == 180
    formation = Formation(2, 4, FLOW, 1.0)
    assert formation.label == "◎○ − 相手 4頭・流し・期待値 1.0 以上・12点まで" and formation.axis_limit == 1 and formation.partner_limit == 5
    assert Formation(1, 0.25).by_threshold and Formation(1, 0.25).threshold_column == "n25" and Formation(1, 2).max_points == 12
    assert Formation(2, 0.5, max_points=1).label == "◎○ − 相手 確率 50% 以上の馬・流し・絞らない・1点まで"


def _combos(shape_count: int) -> pd.DataFrame:
    """位置の組み合わせ。pos は 0（◎）・1（○）・2（▲）・5（相手の外）・NaN（消）。"""
    if shape_count == 1:
        return pd.DataFrame({"pos1": [0, 1, 2, 5, np.nan]})
    if shape_count == 2:
        return pd.DataFrame({"pos1": [0, 1, 0, 1, 5, 0, 1], "pos2": [1, 0, 5, 2, 2, 2, 5]})
    return pd.DataFrame({"pos1": [0, 0, 1, 0, 1, 5], "pos2": [1, 1, 2, 2, 0, 0], "pos3": [2, 5, 0, 3, 3, 1]})


def test_型の判定は券種の形ごとに軸と相手を見る() -> None:
    one = Formation(1, 2)       # 軸 ◎、相手は位置 1・2
    assert FormationMask("単").of_rows(_combos(1), one).tolist() == [True, False, False, False, False]
    assert FormationMask("単").of_rows(_combos(1), Formation(3, 2)).tolist() == [True, True, True, False, False]
    # 確率の線: 線以上の馬が 5頭のレースなら位置 5 まで相手、2頭なら位置 2 まで（軸 ◎ の上限 0 より大きいほう）
    pair_counts = _combos(2).assign(n25=[5, 5, 5, 5, 5, 2, 2])
    assert FormationMask("順不同2").of_rows(pair_counts, Formation(1, 0.25)).tolist() == [True, True, True, False, False, True, False]
    # 線以上の馬が 0 のレースでも、券種の馬の数（2頭）までは相手にする（位置 1 まで）
    none = _combos(2).assign(n25=0)
    assert FormationMask("順不同2").of_rows(none, Formation(1, 0.25)).tolist() == [True, True, False, False, False, False, False]
    assert FormationMask("順不同3").of_rows(_combos(3).assign(n50=0), Formation(1, 0.5)).tolist() == [True, False, True, False, False, False]
    pair = _combos(2)
    # 順不同2: どちらかが軸で両方が軸か相手。(0,1) (1,0) は真、(0,5) は 5 が外、(1,2) は軸が無い、(5,2) 外、(0,2) 真、(1,5) 偽
    assert FormationMask("順不同2").of_rows(pair, one).tolist() == [True, True, False, False, False, True, False]
    assert FormationMask("順不同2").of_rows(pair, Formation(2, 1)).tolist() == [True, True, False, True, False, True, False]
    # 順序2: 1頭目が軸で2頭目が軸か相手
    assert FormationMask("順序2").of_rows(pair, one).tolist() == [True, False, False, False, False, True, False]
    triple = _combos(3)
    flow = Formation(1, 3, FLOW)       # 相手は位置 1〜3
    double = Formation(2, 3, DOUBLE_AXIS)   # 軸 ◎○、2列目も軸、3列目は位置 2〜4 まで
    assert FormationMask("順不同3").of_rows(triple, flow).tolist() == [True, False, True, True, True, False]
    assert FormationMask("順不同3").of_rows(triple, double).tolist() == [True, False, True, False, True, False]
    assert FormationMask("順序3").of_rows(triple, flow).tolist() == [True, False, False, True, False, False]
    assert FormationMask("順序3").of_rows(triple, double).tolist() == [True, False, False, False, True, False]


def test_買う組は線で絞り_届かないレースは1点残し_トリガミを外す() -> None:
    combos = pd.DataFrame({
        "race_id": ["A", "A", "A", "B", "B", "C", "C"], "value": [1.3, 0.9, 1.1, 0.8, 0.7, 1.5, np.nan],
        "odds": [2.0, 30.0, 10.0, 1.5, 40.0, 5.0, np.nan],
    })
    in_formation = np.array([True, True, True, True, True, True, True])
    picker = TicketPicker()
    # 線なし: A は3点だが 2.0倍 ≤ 3点でトリガミ → 外す（残り2点: 30・10 は 2 より大きい）。B は 1.5倍 ≤ 2点で外し、40 は残る。C はオッズ無しを外す
    assert picker.pick(combos, in_formation, None).tolist() == [False, True, True, False, True, True, False]
    # 線 1.0: A は 1.3 と 1.1 の2点だが、1.3 の組は 2.0倍 ≤ 2点でトリガミ → 外す。B は届かないので期待値がいちばん高い 0.8 を1点（1.5倍 > 1点で残る）、C は 1.5
    assert picker.pick(combos, in_formation, 1.0).tolist() == [False, False, True, True, False, True, False]
    assert not picker.pick(combos, np.zeros(7, dtype=bool), None).any()
    # 上限 1点: A は期待値がいちばん高い 1.3 だけ（1点なら 2.0倍 > 1 で残る）、B は 0.8、C は 1.5
    assert picker.pick(combos, in_formation, None, max_points=1).tolist() == [True, False, False, True, False, True, False]


def test_開催日ごとの集計は点数と払戻と買ったレースと当たったレース() -> None:
    combos = pd.DataFrame({
        "cell": ["S/A", "S/A", "S/A", "B/C"], "race_date": [pd.Timestamp("2025-01-05")] * 3 + [pd.Timestamp("2025-01-06")],
        "race_id": ["A", "A", "B", "C"], "payout": [0.0, 300.0, 0.0, 0.0],
    })
    table = DayTable(["S/A", "B/C"], [pd.Timestamp("2025-01-05"), pd.Timestamp("2025-01-06")])
    table.add(combos, np.array([True, True, True, False]))
    assert table.values[0, 0].tolist() == [3.0, 300.0, 2.0, 1.0] and table.values[1, 1, POINTS] == 0
    assert table.recovery() == pytest.approx(1.0) and table.hit_rate() == pytest.approx(0.5)
    assert np.isnan(table.recovery(np.array([1])))
    assert (POINTS, PAYOUT, RACES, HIT_RACES) == (0, 1, 2, 3)


def test_回収率の下の端は開催日の選び直しで出す() -> None:
    bootstrap = RecoveryBootstrap(days=3, rounds=200, seed=1)
    stakes = np.array([[100.0, 100.0, 100.0], [100.0, 100.0, 100.0], [0.0, 0.0, 0.0]])
    payouts = np.array([[150.0, 150.0, 150.0], [0.0, 0.0, 450.0], [0.0, 0.0, 0.0]])
    lower = bootstrap.lower(stakes, payouts)
    assert lower[0] == pytest.approx(1.5) and lower[1] < 1.5 and np.isnan(lower[2])
