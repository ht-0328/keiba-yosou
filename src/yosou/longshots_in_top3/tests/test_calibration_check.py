"""確率のずれの確認（設計書 16 の 4）。保存したモデルで検証・テストの期間を予測し、確率のずれと期待値の当たり具合を表にする。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import PeriodSplitter, SplitData, TrainingData, TrainingPeriod
from yosou.shared.dataset.column_names import PLACE_ODDS_LOW, PLACE_PAYOUT, WIN_ODDS
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES, EnsembleModel
from yosou.shared.place_value import PLACE_VALUE, PlaceExpectedValue, PlacePriceEstimator
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import CalibrationCheck, SegmentedHoldoutPrediction
from yosou.shared.workflow.calibration_check import PART, PART_TEST, PART_VALID, PROBABILITY, SEGMENT, TIMING

from ..command import CommandLine
from ..dataset import LONGSHOT_ZONE, LongshotZone
from ..workflow import SEGMENTS, TIMINGS

BIG = LongshotZone.BIG.label


def _with_place_odds(data: TrainingData) -> TrainingData:
    """合成DB には複勝オッズが無いので、単勝オッズの 3分の1（1.1倍以上）を複勝の最低オッズとして足す。"""
    odds = (pd.to_numeric(data.evaluation[WIN_ODDS], errors="coerce") / 3).clip(lower=1.1)
    return replace(data, evaluation=data.evaluation.assign(**{PLACE_ODDS_LOW: odds}))


@pytest.fixture(scope="module")
def check_frame(trained, training_data: TrainingData, season_period: TrainingPeriod):
    """学習したモデルで、検証とテストの期間を3つの時点で予測した材料の表。"""
    models, _ = trained
    parts = PeriodSplitter(season_period).split(training_data)
    split = SplitData(*(_with_place_odds(part) for part in (parts.train, parts.valid, parts.test)))
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


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_reports_the_calibration(season_db: Path, fast_settings_path: Path, tmp_path: Path):
    period = ["--warmup-from", "2023-10-07", "--train-from", "2024-01-01", "--valid-from", "2024-07-01",
              "--test-from", "2024-10-01"]
    common = ["--db", str(season_db), "--models", str(tmp_path / "models")]
    assert _run_command(["train", "--config", str(fast_settings_path), *period, *common,
                         "--out", str(tmp_path / "train.md")]) == 0
    out = tmp_path / "calibration.md"
    assert _run_command(["calibration", *period, *common, "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    for title in ("確率のずれのまとめ", "確率の帯ごとのずれ", "確定単勝人気ごとのずれ", "複勝の期待値の帯ごとの回収率"):
        assert title in text
    assert "| 木曜 | 中穴 | 検証 |" in text and "| 当日 | 大穴 | テスト |" in text
