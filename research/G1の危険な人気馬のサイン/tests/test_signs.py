"""サインの材料・サイン・事例の表・学習に使うレースの範囲。合成データだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from G1の危険な人気馬のサイン.analysis.danger_signs import DangerSigns
from G1の危険な人気馬のサイン.analysis.g1_favorites import LOST, G1Favorites
from G1の危険な人気馬のサイン.analysis.gate_bias_features import GateBiasFeatures
from G1の危険な人気馬のサイン.analysis.horse_history_features import HorseHistoryFeatures
from G1の危険な人気馬のサイン.analysis.sign_case_report import SignCaseReport
from G1の危険な人気馬のサイン.analysis.sign_columns import (
    BEST_PLACED_DISTANCE_GAP,
    G1_BEST_FINISH,
    G1_PLACES,
    G1_RUNS,
    GRADED_WINS,
    LAST5_NEAR_MISSES,
    LAST5_WINS,
    MEETING_GATE_EDGE,
    RUNS_SINCE_WIN,
    SAME_STAKES_RUNS,
    SIGN_COLUMNS,
    SIGN_COUNT,
)
from G1の危険な人気馬のサイン.analysis.sign_table_builder import SignTableBuilder
from G1の危険な人気馬のサイン.analysis.sign_variants import SIGN_VARIANTS


def _runs(rows: list[dict]) -> pd.DataFrame:
    """1行 = 1頭の出走の合成の表（``RunHistoryRepository`` と同じ列）。書いていない列は既定の値。"""
    defaults = {
        "venue_code": "05", "track_code": "11", "surface": "芝", "distance_m": 2000, "grade_code": "", "class_order": 6,
        "field_size": 12, "horse_no": 1, "sex": "牡", "age": 4, "popularity": 1.0, "win_odds": 2.0, "finish": 1.0,
        "mixed_sex": False, "prev_distance_m": np.nan, "prev_finish": np.nan, "prev_popularity": np.nan,
        "win_payout": 0, "place_payout": 0, "stakes_no": None,
    }
    frame = pd.DataFrame([{**defaults, **row} for row in rows])
    frame["race_date"] = pd.to_datetime(frame["race_date"])
    return frame


def _one_horse_history() -> pd.DataFrame:
    """1頭の6走。G2 を勝ち、G1 で 2回負け、同じ G1 にもう一度出る。"""
    rows = [
        {"race_id": "2020010105010101", "race_date": "2020-01-01", "finish": 1.0, "distance_m": 1600},
        {"race_id": "2020020105010101", "race_date": "2020-02-01", "finish": 1.0, "distance_m": 1800, "grade_code": "B",
         "stakes_no": "0100"},
        {"race_id": "2020030105010101", "race_date": "2020-03-01", "finish": 5.0, "distance_m": 2000, "grade_code": "A",
         "stakes_no": "0200"},
        {"race_id": "2020040105010101", "race_date": "2020-04-01", "finish": 2.0, "distance_m": 2000},
        {"race_id": "2021030105010101", "race_date": "2021-03-01", "finish": 4.0, "distance_m": 2000, "grade_code": "A",
         "stakes_no": "0200"},
        {"race_id": "2022030105010101", "race_date": "2022-03-01", "finish": 9.0, "distance_m": 2400, "grade_code": "A",
         "stakes_no": "0200"},
    ]
    return _runs([{**row, "horse_id": "H1"} for row in rows])


def test_history_uses_only_the_runs_before():
    history = HorseHistoryFeatures().compute(_one_horse_history())
    last = history.iloc[-1]
    assert last[G1_RUNS] == 2 and last[G1_PLACES] == 0 and last[G1_BEST_FINISH] == 4
    assert last[GRADED_WINS] == 1
    # 3着以内に来た最長距離は 4走目の 2000m（2着）。今回 2400m なので +400
    assert last[BEST_PLACED_DISTANCE_GAP] == 400
    assert last[SAME_STAKES_RUNS] == 2
    # 近5走: 1・1・5・2・4 → 2〜5着が3回、1着が2回。最後の勝ちから 3走
    assert last[LAST5_NEAR_MISSES] == 3 and last[LAST5_WINS] == 2 and last[RUNS_SINCE_WIN] == 3
    first = history.iloc[0]
    assert first[G1_RUNS] == 0 and np.isnan(first[BEST_PLACED_DISTANCE_GAP]) and first[RUNS_SINCE_WIN] == 0


def test_meeting_gate_edge_uses_only_the_earlier_days():
    rows = []
    # 1日目: 外の帯（馬番 9〜12）ばかり 3着以内。2日目のレースの値に効き、1日目の値には効かない
    for race in range(1, 7):
        for no in range(1, 13):
            rows.append({"race_id": f"20200101050101{race:02d}", "race_date": "2020-01-01", "horse_id": f"A{race}-{no}",
                         "horse_no": no, "finish": float(13 - no)})
    for no in range(1, 13):
        rows.append({"race_id": "2020010205010201", "race_date": "2020-01-02", "horse_id": f"B-{no}", "horse_no": no,
                     "finish": float(no)})
    runs = _runs(rows)
    edge = GateBiasFeatures().compute(runs)[MEETING_GATE_EDGE]
    day_two = runs["race_date"].eq(pd.Timestamp("2020-01-02"))
    assert edge[~day_two].isna().all()
    assert edge[day_two & runs["horse_no"].eq(12)].iloc[0] > 0.5
    assert edge[day_two & runs["horse_no"].eq(1)].iloc[0] < -0.5
    assert edge[day_two & runs["horse_no"].eq(6)].iloc[0] == 0


def test_signs_follow_their_lines():
    table = SignTableBuilder().build(_one_horse_history())
    last = table.iloc[-1]
    assert last["サイン1 距離適性の外"] == 1      # 3着以内の最長より 400m 長い
    assert last["サイン3 G1の格がない"] == 1      # G2 を勝ったが G1 で3着以内なし
    assert last["サイン4 重度のリピーター"] == 1  # 同じ G1 は3回目
    assert last["サイン5 惜しい競馬を繰り返す"] == 0  # 近5走に1着がある
    assert last[SIGN_COUNT] == table.loc[table.index[-1], list(SIGN_COLUMNS)].sum()


def test_strong_favorite_sign_marks_only_the_second_and_third_favorites():
    frame = pd.DataFrame({"popularity": [1, 2, 3, 4], "1番人気の単勝オッズ": [1.8] * 4})
    for column in ("今回の距離 − 3着以内に来た最長距離", "開催の先の日の、自分の枠の側の有利さ", "コースの過去の、自分の枠の帯の有利さ",
                   "G1の出走数", "G1の3着以内の数", "G2・G3の勝利数", "同じ重賞への出走数", "近5走の2〜5着の数", "近5走の1着の数",
                   "重賞の3着以内の数", "勝利数", "前走のクラスの並び", "3歳牝馬の牡馬との混合戦", "前走からの距離の延長", "前々走の着順",
                   "prev_finish", "prev_popularity"):
        frame[column] = np.nan
    signs = DangerSigns().compute(frame)
    assert signs["サイン10 断然人気の陰の2・3番人気"].tolist() == [0, 1, 1, 0]
    assert signs[SIGN_COUNT].tolist() == [0, 1, 1, 0]


def test_g1_favorites_and_case_report():
    rows = []
    for year in (2015, 2021):
        for no in range(1, 15):
            rows.append({"race_id": f"{year}0601050101{11:02d}", "race_date": f"{year}-06-01", "horse_id": f"{year}-{no}",
                         "horse_no": no, "field_size": 14, "popularity": float(no), "finish": float(15 - no),
                         "grade_code": "A", "win_payout": 0, "place_payout": 0})
    table = SignTableBuilder().build(_runs(rows))
    chosen = G1Favorites().select(table)
    # 14頭立てなので 1〜5番人気
    assert len(chosen) == 10 and chosen[LOST].eq(1).all()
    tables = SignCaseReport().tables(table)
    assert [len(t) for t in tables[:1]] == [1]
    assert len(tables[1]) == len(SIGN_COLUMNS)


def test_variants_cover_three_scopes_with_and_without_signs():
    keys = [variant.key for variant in SIGN_VARIANTS]
    assert keys == ["odds_only", "g1-current", "g1-signs", "stakes-current", "stakes-signs", "all-current", "all-signs"]
    signs = next(variant for variant in SIGN_VARIANTS if variant.key == "g1-signs")
    current = next(variant for variant in SIGN_VARIANTS if variant.key == "g1-current")
    assert len(signs.variant.columns) == len(current.variant.columns) + 30
    assert signs.variant.segment_column is None
    assert next(variant for variant in SIGN_VARIANTS if variant.key == "all-current").variant.segment_column is not None
