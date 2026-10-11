"""回顧（不利の判定・前走の不利・保存・前走の引き方）。DB は一時フォルダの DuckDB だけ、元DB は使わない。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from yosou.development_score import AdvantageTable
from yosou.development_score import names as score_names
from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData
from yosou.shared.feature import BASE_FEATURES, FeatureCatalog, PredictionTiming
from yosou.track_bias import names as bias_names

from .. import names
from ..early_positions import EarlyPositions
from ..features import PREVIOUS_BIAS, PREVIOUS_LATE_START, PREVIOUS_MAX, PREVIOUS_PACE, PREVIOUS_REVIEW
from ..handicap_lines import HandicapLines
from ..previous_handicap_attachment import PreviousHandicapAttachment
from ..previous_handicap_columns import PreviousHandicapColumns
from ..previous_handicap_free_data import PreviousHandicapFreeData
from ..result_style import ResultStyle
from ..review_store import ReviewStore
from ..run_handicaps import RunHandicaps


def test_程度は_線からどれだけ超えたかで小中大_4着以下でなければ0_値が無ければ欠損値():
    lines = HandicapLines()
    late = lines.degree(pd.Series([0.39, 0.4, 0.5, 0.65, 0.9, np.nan, 0.9]), pd.Series([5, 5, 5, 5, 5, 5, 2]), 0.4, 0.1)
    assert late.tolist()[:5] == [0.0, 1.0, 2.0, 3.0, 3.0] and np.isnan(late[5]) and late[6] == 0.0
    pace = lines.degree(pd.Series([-0.005, -0.01, -0.02, -0.031]), pd.Series([4, 4, 4, 4]), -0.01, 0.01)
    assert pace.tolist() == [0.0, 1.0, 2.0, 3.0]


def test_序盤の位置と結果の脚質():
    runs = pd.DataFrame({"horse_id": ["a", "a", "a", "b"], "race_date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-03-01"]),
                         "race_id": ["r1", "r2", "r3", "r3"], "first_corner_rank": [1, 3, 11, np.nan], "field_size": [11, 11, 11, 11]})
    early = EarlyPositions().of(runs)
    assert early["actual"].round(2).tolist()[:3] == [0.0, 0.2, 1.0] and np.isnan(early.loc[0, "expected"]) and early.loc[2, "expected"] == 0.1
    assert np.isnan(early.loc[3, "actual"])
    assert ResultStyle().of(runs).tolist() == [score_names.LEAD, score_names.FRONT, score_names.BACK, None]


def _prepared() -> pd.DataFrame:
    # 1頭が 2024年に4走。r4 で大きく出遅れ（近3走は先頭付近、今回は最後方）、4着以下
    rows = []
    for i, (rid, rank, finish) in enumerate([("r1", 1, 1), ("r2", 2, 2), ("r3", 1, 3), ("r4", 10, 8)]):
        rows.append({"race_id": rid, "race_date": pd.Timestamp(f"2024-0{i + 1}-01"), "horse_id": "a", "horse_no": 5, "field_size": 10,
                     "first_corner_rank": rank, "corner4": rank, "finish": finish, score_names.PACE: score_names.SLOW,
                     score_names.VENUE_CODE: "05", score_names.SURFACE: "芝"})
    return pd.DataFrame(rows)


def _table() -> AdvantageTable:
    cells = [(style, pace, 0.0) for style in score_names.STYLES for pace in score_names.PACES]
    frame = pd.DataFrame([{score_names.STYLE: s, score_names.PACE: p, score_names.VENUE_CODE: "05", score_names.SURFACE: "芝",
                           score_names.COUNT: 100, score_names.RAW_GAP: v, score_names.POOL_GAP: v, score_names.GAP: v} for s, p, v in cells])
    frame.loc[(frame[score_names.STYLE] == score_names.BACK) & (frame[score_names.PACE] == score_names.SLOW), score_names.GAP] = -0.025
    return AdvantageTable(frame, frame.drop(columns=[score_names.VENUE_CODE, score_names.SURFACE]))


def test_出走ごとの不利は_出遅れと展開とバイアスを線で判定し_種類と程度と次走の扱いを付ける():
    used = pd.DataFrame({bias_names.USED_INNER: 0.0, bias_names.USED_FRONT: 0.3, bias_names.COURSE_INNER: 0.0, bias_names.COURSE_FRONT: 0.2},
                        index=["r1", "r2", "r3", "r4"])
    table = RunHandicaps().of(_prepared(), _table(), used)
    last = table.iloc[3]
    # 出遅れ: 近3走の平均 0.037 に対して今回 1.0 → 0.96 後ろ → 大。展開: 追込 × スロー = −0.025 → 中。バイアス: (0.3−0.2) × (0.5−1.0) = −0.05 → 大
    assert last[names.LATE_START_DEGREE] == 3 and last[names.PACE_DEGREE] == 2 and last[names.BIAS_DEGREE] == 3
    assert last[names.HANDICAPS] == "出遅れ・展開が向かなかった・バイアスと逆" and last[names.DEGREE] == 3 and last[names.NEXT_RUN] == names.REVIEW
    # 3着以内に来た走は不利と数えない（r3 は逃げ × スロー で表 G は 0）
    assert table.iloc[2][names.DEGREE] == 0 and table.iloc[2][names.HANDICAPS] == "" and table.iloc[2][names.NEXT_RUN] == names.NONE
    assert np.isnan(table.iloc[0][names.LATE_START_GAP])   # 初出走は見込みの位置が無い


def test_前走の不利は_馬ごとに1つ前の走の程度を取り_近2走の最大も出す():
    handicaps = pd.DataFrame({
        names.RACE_ID: ["r1", "r2", "r3", "s1"], names.RACE_DATE: pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-02-01"]),
        names.HORSE_ID: ["a", "a", "a", "b"], names.LATE_START_DEGREE: [0, 3, 0, 1], names.PACE_DEGREE: [0, 0, 2, 0], names.BIAS_DEGREE: [1, 0, 0, 0],
    })
    previous = PreviousHandicapColumns().of(handicaps).set_index(names.RACE_ID)
    assert np.isnan(previous.loc["r1", PREVIOUS_LATE_START]) and np.isnan(previous.loc["s1", PREVIOUS_MAX])
    assert previous.loc["r2", PREVIOUS_BIAS] == 1 and previous.loc["r2", PREVIOUS_REVIEW] == 0 and previous.loc["r2", PREVIOUS_MAX] == 1
    assert previous.loc["r3", PREVIOUS_LATE_START] == 3 and previous.loc["r3", PREVIOUS_REVIEW] == 1 and previous.loc["r3", PREVIOUS_MAX] == 3
    assert previous.loc["r3", PREVIOUS_PACE] == 0


def test_予測用データに前走の不利を足し_外せば消える():
    ids = pd.DataFrame({RACE_ID: ["r9", "r9"], HORSE_ID: ["a", "b"]}, index=[5, 6])
    data = PredictionData(ids, pd.DataFrame({BASE_FEATURES[0].name: [1.0, 1.0]}, index=[5, 6]), PredictionTiming.DAY_BEFORE,
                          FeatureCatalog(BASE_FEATURES[:1]))
    previous = pd.DataFrame({names.RACE_ID: ["r9"], names.HORSE_ID: ["a"], PREVIOUS_LATE_START: [2.0], PREVIOUS_PACE: [0.0], PREVIOUS_BIAS: [0.0],
                             PREVIOUS_REVIEW: [1.0], PREVIOUS_MAX: [2.0]})
    attached = PreviousHandicapAttachment().apply(data, previous)
    assert attached.features.loc[5, PREVIOUS_REVIEW] == 1.0 and np.isnan(attached.features.loc[6, PREVIOUS_REVIEW])
    assert attached.catalog.names[-1] == PREVIOUS_MAX
    freed = PreviousHandicapFreeData().prediction(attached)
    assert PREVIOUS_MAX not in freed.features.columns and PREVIOUS_MAX not in freed.catalog.names


def test_保存した表は_同じ鍵の行を置き換え_範囲を覚える(tmp_path: Path):
    store = ReviewStore(tmp_path / "review.duckdb")
    assert store.as_of() is None
    rows = pd.DataFrame({names.RACE_ID: ["r1", "r1"], names.HORSE_ID: ["a", "b"], names.RACE_DATE: [date(2024, 1, 1)] * 2,
                         names.HANDICAPS: ["出遅れ", "展開が向かなかった"], names.DEGREE: [3, 1], names.NEXT_RUN: [names.REVIEW, names.NONE],
                         names.LATE_START_DEGREE: [3, 0], names.PACE_DEGREE: [0, 1], names.BIAS_DEGREE: [0, 0]})
    assert store.write(names.HORSES_TABLE, rows) == 2
    again = rows.iloc[[0]].assign(**{names.DEGREE: 2})
    store.write(names.HORSES_TABLE, again)
    saved = store.read(names.HORSES_TABLE, f"{names.RACE_ID} = ?", ["r1"]).sort_values(names.HORSE_ID)
    assert saved[names.DEGREE].tolist() == [2, 1] and len(saved) == 2
    store.set_as_of(date(2024, 1, 1))
    assert store.as_of() == date(2024, 1, 1)
    assert store.write(names.BETS_TABLE, pd.DataFrame()) == 0
