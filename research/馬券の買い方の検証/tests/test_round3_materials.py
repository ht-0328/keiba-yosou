"""契約: 3回目の材料表は、3つの1頭ごとの予測と答えを 区切り × 期間 × レース × 馬 で結合し、レースごとに重賞かと荒れ具合を付け、ファイルに往復する。"""

import numpy as np
import pandas as pd

from yosou.shared.dataset import FIELD_SIZE, HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TOP3
from yosou.shared.dataset.column_names import FINISH, PLACE_ODDS_HIGH, PLACE_ODDS_LOW, PLACE_PAYOUT, POPULARITY, WIN_ODDS
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE
from yosou.upset_level.dataset import BetType

from 馬券の買い方の検証.analysis.value_betting import MaterialsStore, RaceTableBuilder, Round3Materials, RunnerTableBuilder, TruthTableReader
from 馬券の買い方の検証.analysis.value_betting import columns as c
from 馬券の買い方の検証.analysis.value_betting.runner_table_builder import COLUMNS

from round3_fixtures import materials

_W1, _W2 = "2023年前半", "2023年後半"
_R1 = "2023010705010101"


def _prediction(window: str, part: str, horses, probabilities, segments=None) -> pd.DataFrame:
    return pd.DataFrame({
        "レースID": _R1, "開催日": pd.Timestamp("2023-01-07"), "馬ID": [f"H{horse}" for horse in horses], "馬番": horses,
        "確率": probabilities, "区切り": window, "期間": part, "区分": segments if segments is not None else "全体",
    })


def _truth() -> pd.DataFrame:
    return pd.DataFrame({
        RACE_ID: [_R1] * 3, RACE_DATE: pd.Timestamp("2023-01-07"), HORSE_ID: ["H1", "H2", "H3"], FINISH: [1, 5, 2],
        WIN_ODDS: [2.0, 4.5, 15.0], POPULARITY: [1, 2, 3], PLACE_PAYOUT: [110.0, 0.0, 400.0], PLACE_ODDS_LOW: [1.1, 1.8, 4.0],
        PLACE_ODDS_HIGH: [1.3, 2.4, 6.5], FIELD_SIZE: 16, TOP2_RATE: [0.5, 0.3, 0.1], TOP3_RATE: [0.7, 0.45, 0.15], TOP3: [1, 0, 1],
    })


def test_runner_table_joins_predictions_by_window_part_race_and_horse():
    form = pd.concat([_prediction(_W1, "テスト", [1, 2, 3], [0.6, 0.4, 0.2]), _prediction(_W2, "検証", [1, 2, 3], [0.65, 0.35, 0.25])])
    longshots = _prediction(_W1, "テスト", [3], [0.22], ["中穴"])
    favorites = _prediction(_W1, "テスト", [1, 2], [0.35, 0.6])
    runners = RunnerTableBuilder().build(form, _truth(), longshots, favorites)
    assert list(runners.columns) == list(COLUMNS) and len(runners) == 6
    first = runners[(runners[c.WINDOW] == _W1) & (runners[c.PART] == "テスト")].set_index(c.HORSE_NO)
    assert first.loc[3, c.LONGSHOT_ZONE] == "中穴" and first.loc[3, c.LONGSHOT_PROB] == 0.22 and np.isnan(first.loc[1, c.LONGSHOT_PROB])
    assert first.loc[2, c.DANGER_PROB] == 0.6 and np.isnan(first.loc[3, c.DANGER_PROB])
    assert first.loc[3, c.PLACE_PAYOUT] == 400.0 and first.loc[3, c.TOP3] == 1 and first.loc[1, c.FIELD_SIZE] == 16
    # 次の区切りの検証の行には、その区切りの穴馬・人気馬の予測だけが付く（ここでは無いので欠損）
    second = runners[runners[c.WINDOW] == _W2].set_index(c.HORSE_NO)
    assert second[c.LONGSHOT_PROB].isna().all() and second[c.DANGER_PROB].isna().all() and second.loc[1, c.FORM_PROB] == 0.65


def test_race_table_has_graded_flag_and_upset_probability_per_bet():
    runners = RunnerTableBuilder().build(_prediction(_W1, "テスト", [1, 2, 3], [0.6, 0.4, 0.2]), _truth(),
                                         _prediction(_W1, "テスト", [], [], []), _prediction(_W1, "テスト", [], []))
    upset = pd.DataFrame([
        {"レースID": _R1, "開催日": pd.Timestamp("2023-01-07"), "固い": 0.3, "中荒れ": 0.4, "大荒れ": 0.2, "超荒れ": 0.1,
         "区切り": _W1, "期間": "テスト", "券種": bet.label} for bet in BetType
    ])
    facts = pd.DataFrame({"race_id": [_R1, "other"], "grade_code": ["A", ""]})
    races = RaceTableBuilder().build(runners, upset, facts)
    assert len(races) == 1 and bool(races.loc[0, c.IS_GRADED]) is True
    assert races.loc[0, c.upset_column(BetType.TRIO)] == 0.7 and races.loc[0, c.upset_level_column(BetType.WIN)] == "中荒れ"
    without = RaceTableBuilder().build(runners, upset.iloc[0:0], facts.iloc[0:0])
    assert bool(without.loc[0, c.IS_GRADED]) is False and np.isnan(without.loc[0, c.upset_column(BetType.TRIO)])


def test_truth_table_reader_reads_the_three_parts_and_drops_duplicates(tmp_path):
    truth = _truth()
    duplicated = pd.concat([truth, truth.iloc[[0]]], ignore_index=True)
    duplicated[[RACE_ID, RACE_DATE, HORSE_ID]].assign(馬番=[1, 2, 3, 1], 馬名="x").to_pickle(tmp_path / "ids.pkl")
    duplicated[[FINISH, WIN_ODDS, POPULARITY, PLACE_PAYOUT, PLACE_ODDS_LOW, PLACE_ODDS_HIGH, FIELD_SIZE, TOP2_RATE, TOP3_RATE]] \
        .assign(オッズから見た勝率=0.2).to_pickle(tmp_path / "evaluation.pkl")
    duplicated[[TOP3]].assign(**{"1着": 0, "複勝的中": 0}).to_pickle(tmp_path / "targets.pkl")
    read = TruthTableReader(tmp_path).read()
    assert len(read) == 3 and read[RACE_ID].map(type).eq(str).all() and read[HORSE_ID].map(type).eq(str).all()
    assert set(read.columns) >= {RACE_ID, HORSE_ID, PLACE_PAYOUT, TOP3, FIELD_SIZE}


def test_materials_store_round_trips_and_materials_slice_by_window_and_part(tmp_path):
    built = materials(days=2, races=2)
    store = MaterialsStore(tmp_path / "materials")
    assert not store.exists()
    store.write(built, {"sources": {"form": "x"}})
    restored = store.read()
    assert isinstance(restored, Round3Materials) and store.exists()
    assert restored.window_names == [_W1, _W2]
    assert len(restored.runners_of(_W1, c.PART_TEST)) == 2 * 2 * 12 and len(restored.races_of(_W2, c.PART_VALID)) == 4
    assert restored.runners_of("無い区切り", c.PART_TEST).empty
    pd.testing.assert_frame_equal(restored.price_history, built.price_history)
