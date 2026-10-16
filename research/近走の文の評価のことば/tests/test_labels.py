"""ことばと苦手の傾向の付け方、成績の数え方。値は架空。"""

from __future__ import annotations

import pandas as pd

from 近走の文.evaluation_words import BIG_LOSSES, IMPROVING
from 近走の文の評価のことば.analysis.label_tally import LabelTally
from 近走の文の評価のことば.analysis.report_writer import ReportWriter
from 近走の文の評価のことば.analysis.tendency_labels import DISTANCE, HEAVY, LINES, SURFACE, TendencyLabels
from 近走の文の評価のことば.analysis.word_labels import LONGSHOT_RECORD, STRONG_LOSS, WORD_SIDES, WordLabels


def _frame(rows: list[dict]) -> pd.DataFrame:
    """馬ごと・日付順の走の表。足りない列は既定で埋める。"""
    defaults = {"finish": 5.0, "time_diff": 1.0, "last3f_rank": 8.0, "popularity": 5.0, "handicap": False, "surface": "芝",
                "distance_m": 1600.0, "condition": "良", "win_payout": 0.0, "place_payout": 0.0}
    frame = pd.DataFrame([{**defaults, **row} for row in rows])
    frame["race_date"] = pd.to_datetime(frame["race_date"])
    frame["placed"] = (frame["finish"] <= 3).astype(float)
    frame["year"] = frame["race_date"].dt.year
    return frame


def test_words_come_only_from_the_runs_before():
    frame = _frame([
        {"horse_id": "a", "race_id": "1", "race_date": "2026-01-01", "finish": 5, "time_diff": 0.2, "handicap": True},
        {"horse_id": "a", "race_id": "2", "race_date": "2026-02-01", "finish": 4, "time_diff": 0.1, "last3f_rank": 1},
        {"horse_id": "a", "race_id": "3", "race_date": "2026-03-01", "finish": 1, "time_diff": -0.1, "popularity": 12},
        {"horse_id": "a", "race_id": "4", "race_date": "2026-04-01", "finish": 9, "time_diff": 1.5},
        {"horse_id": "a", "race_id": "5", "race_date": "2026-05-01", "finish": 8, "time_diff": 1.2},
        {"horse_id": "a", "race_id": "6", "race_date": "2026-06-01"},
        {"horse_id": "b", "race_id": "7", "race_date": "2026-01-01", "finish": 4, "time_diff": 0.3, "handicap": True},
    ])
    labels = WordLabels().of(frame)
    assert set(labels.columns) == set(WORD_SIDES)
    # 2走目: 前走は 5着・着差 0.2・不利あり → 負けて強し（不利あり）。3走目: 前走は 4着・着差 0.1・上がり1位 → 負けて強し（上がり上位）
    assert labels[f"{STRONG_LOSS}（不利あり）"].tolist() == [False, True, False, False, False, False, False]
    assert labels[f"{STRONG_LOSS}（上がり上位）"].tolist() == [False, False, True, False, False, False, False]
    assert labels[STRONG_LOSS].tolist() == [False, True, True, False, False, False, False]
    # 4走目: 近3走の着差 0.2 → 0.1 → -0.1 と縮んでいる → 上向き
    assert labels[IMPROVING].tolist() == [False, False, False, True, False, False, False]
    # 3走目が 12番人気 1着 → 4〜6走目に 人気薄で好走の実績。6走目: 近2走の着差 1.5・1.2 → 大敗続き
    assert labels[LONGSHOT_RECORD].tolist() == [False, False, False, True, True, True, False]
    assert labels[BIG_LOSSES].tolist() == [False, False, False, False, False, True, False]
    # 馬 b の最初の走は前の走が無いので何も付かない
    assert not labels.iloc[-1].any()


def test_tendencies_need_enough_runs_on_both_sides():
    rows = [{"horse_id": "a", "race_id": str(k), "race_date": f"2025-{k:02d}-01", "condition": "良", "finish": 1} for k in range(1, 4)]
    rows += [{"horse_id": "a", "race_id": str(k), "race_date": f"2025-{k:02d}-01", "condition": "重", "finish": 9} for k in range(4, 7)]
    rows.append({"horse_id": "a", "race_id": "7", "race_date": "2025-07-01", "condition": "不良", "finish": 2})
    rows.append({"horse_id": "a", "race_id": "8", "race_date": "2025-08-01", "condition": "良", "finish": 2})
    labels = TendencyLabels().of(_frame(rows))
    assert set(labels.columns) == {f"{kind}｜{line.label}" for kind in (HEAVY, SURFACE, DISTANCE) for line in LINES}
    strict = labels[f"{HEAVY}｜{LINES[0].label}"]
    # 7走目: 前の重が 0-0-0-3、良が 3-0-0-0 で両側3走以上・差 1.0 → 苦手で今回も重 → True。8走目は良なので False
    assert strict.tolist() == [False] * 6 + [True, False]
    loose = labels[f"{HEAVY}｜{LINES[1].label}"]
    # 両側 2走以上なら、6走目（前の重が 0-0-0-2）から True
    assert loose.tolist() == [False] * 5 + [True, True, False]
    # 芝ダ・距離は全部同じなので、相手の側が無く付かない
    assert not labels[[column for column in labels.columns if column.startswith((SURFACE, DISTANCE))]].any().any()


def test_tally_counts_the_gap_against_popularity_and_the_writer_lists_it():
    # 1番人気・2番人気がそれぞれ 10走で、半分が3着以内（期待は 0.5 ずつ）。3着以内の走に複勝 110円、そのうち1走に単勝 200円
    rows = []
    for popularity in (1, 2):
        for k in range(10):
            placed = k < 5
            rows.append({"horse_id": f"{popularity}-{k}", "race_id": "1", "race_date": "2026-01-01", "finish": 2 if placed else 6,
                         "popularity": popularity, "place_payout": 110 if placed else 0, "win_payout": 200 if (placed and k == 0) else 0})
    frame = _frame(rows)
    labels = pd.DataFrame({"良い": frame["placed"] == 1, "悪い": frame["placed"] == 0, "無し": False}, index=frame.index)
    good, bad, none = LabelTally(frame).rows(labels, {"良い": True, "悪い": False, "無し": None})
    # 良いは 10走とも3着以内 → 差 +50pt（標準誤差 15.8pt の2倍以上なので採用）、悪いは 0 → −50pt
    assert good.runs == 10 and good.place_rate == 100 and round(good.gap_points) == 50 and good.adopted is True
    assert bad.runs == 10 and bad.place_rate == 0 and round(bad.gap_points) == -50 and bad.adopted is True
    assert round(good.std_error_points, 1) == 15.8 and round(good.win_return) == 40 and round(good.place_return) == 110
    assert none.runs == 0 and none.adopted is None
    text = ReportWriter().markdown("題", [("全期間", [good, bad, none])], ["注"])
    assert text.startswith("# 題\n\n- 注\n\n## 全期間\n") and "| 良い | 10 | 100.0% | +50.0pt |" in text and "| 無し | 0 | — |" in text
