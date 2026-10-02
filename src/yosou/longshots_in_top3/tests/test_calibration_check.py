"""確率のずれの確認（設計書 16 の 5）。保存したモデルで検証・テストの期間を予測し、確率のずれと期待値の当たり具合を表にする。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from yosou.shared.dataset import PeriodSplitter, TrainingData, TrainingPeriod
from yosou.shared.dataset.column_names import PLACE_ODDS_LOW, PLACE_PAYOUT
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES, EnsembleModel
from yosou.shared.place_value import PLACE_VALUE, PlaceExpectedValue, PlacePriceEstimator
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import CalibrationCheck, SegmentedHoldoutPrediction
from yosou.shared.workflow.calibration_check import PART, PART_TEST, PART_VALID, PROBABILITY, SEGMENT, TIMING

from ..command import CommandLine
from ..command.buy_line_report_table import BuyLineReportTable
from ..dataset import LONGSHOT_ZONE, LongshotZone
from ..workflow import SEGMENTS, TIMINGS

MID, BIG = LongshotZone.MID.label, LongshotZone.BIG.label


@pytest.fixture(scope="module")
def check_frame(trained, training_data: TrainingData, season_period: TrainingPeriod):
    """学習したモデルで、検証とテストの期間を3つの時点で予測した材料の表（複勝オッズは合成DB に足したもの）。"""
    models, _ = trained
    split = PeriodSplitter(season_period).split(training_data)
    estimator = PlacePriceEstimator().fit(split.train.evaluation[PLACE_ODDS_LOW], split.train.evaluation[PLACE_PAYOUT])
    check = CalibrationCheck(SEGMENTS, SegmentedHoldoutPrediction(SEGMENTS, models),
                             PlaceExpectedValue(estimator), TIMINGS)
    return split, check.run(split)


def test_check_predicts_every_timing_on_the_held_out_periods(check_frame):
    split, frame = check_frame
    assert len(frame) == (len(split.valid) + len(split.test)) * len(TIMINGS)
    counts = frame.groupby([TIMING, PART]).size()
    assert all(counts[(timing.label, PART_VALID)] == len(split.valid) for timing in TIMINGS)
    assert all(counts[(timing.label, PART_TEST)] == len(split.test) for timing in TIMINGS)
    assert set(frame[SEGMENT]) == {LongshotZone.MID.label, BIG}
    assert frame[PROBABILITY].between(0, 1, inclusive="neither").all()


def test_check_uses_the_saved_model_of_each_zone(check_frame, trained):
    models, _ = trained
    split, frame = check_frame
    timing = PredictionTiming.RACE_DAY
    big_test = split.test.where(split.test.evaluation[LONGSHOT_ZONE].eq(BIG)).for_timing(timing)
    expected = EnsembleModel(ModelRepository(models / "big", MEMBER_TYPES).load(timing)).predict_proba(big_test)
    chosen = frame[(frame[TIMING] == timing.label) & (frame[PART] == PART_TEST) & (frame[SEGMENT] == BIG)]
    np.testing.assert_allclose(chosen[PROBABILITY].to_numpy(), expected)


def test_check_gives_the_expected_value_only_when_the_odds_are_known(check_frame):
    _, frame = check_frame
    thursday = frame[frame[TIMING] == PredictionTiming.THURSDAY.label]
    race_day = frame[frame[TIMING] == PredictionTiming.RACE_DAY.label]
    # 木曜はオッズが分からないので、予測と同じく期待値を出さない
    assert thursday[PLACE_VALUE].isna().all() and race_day[PLACE_VALUE].notna().any()


def test_buy_line_report_counts_the_horses_over_the_line(check_frame):
    _, frame = check_frame
    lines = {PredictionTiming.RACE_DAY: {MID: 0.0}}
    table = BuyLineReportTable(frame, lines, [MID, BIG]).table()
    rows = {tuple(row[:3]): row for row in table.rows}
    race_day_test = frame[(frame[TIMING] == "当日") & (frame[PART] == PART_TEST)]
    # 線 0 の中穴は、期待値の出る中穴を全部買う。線の無い大穴と、線の無い前日は買わない
    assert rows[("当日", PART_TEST, MID)][4] == int((race_day_test[SEGMENT] == MID).sum())
    assert rows[("当日", PART_TEST, BIG)][3] == "なし" and rows[("当日", PART_TEST, BIG)][4] == 0
    assert rows[("前日", PART_VALID, "全体")][4] == 0
    assert rows[("当日", PART_TEST, "全体")][4] == rows[("当日", PART_TEST, MID)][4]
    # 並びは 時点 → 期間 → 区分（全体は最後）
    assert [tuple(row[:3]) for row in table.rows][:3] == [("前日", PART_VALID, MID), ("前日", PART_VALID, BIG), ("前日", PART_VALID, "全体")]


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_reports_the_calibration(longshot_db: Path, fast_settings_path: Path, tmp_path: Path):
    period = ["--warmup-from", "2023-10-07", "--train-from", "2024-01-01", "--valid-from", "2024-07-01",
              "--test-from", "2024-10-01"]
    common = ["--db", str(longshot_db), "--models", str(tmp_path / "models")]
    assert _run_command(["train", "--config", str(fast_settings_path), *period, *common,
                         "--out", str(tmp_path / "train.md")]) == 0
    out = tmp_path / "calibration.md"
    assert _run_command(["calibration", *period, *common, "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    for title in ("確率のずれのまとめ", "確率の帯ごとのずれ", "確定単勝人気ごとのずれ", "複勝の期待値の帯ごとの回収率"):
        assert title in text
    assert "| 木曜 | 中穴 | 検証 |" in text and "| 当日 | 大穴 | テスト |" in text
    # 学習のときに保存した「買い」の線で買ったときの成績も出す（前日・当日だけ）
    assert "「買い」の線で買ったときの成績" in text and "| 当日 | テスト | 全体 |" in text
