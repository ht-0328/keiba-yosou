"""学習の流れ（設計書 05 の図1）と予測の流れ（図2）、モデルの保存と読み込み、コマンドの入口。"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import numpy as np
import pytest

from 共通 import db

from yosou.shared.dataset import (
    HORSE_NO,
    RACE_ID,
    OddsInput,
    OddsResolver,
    PopularityApplier,
    PopularityInput,
    TrainingData,
)
from yosou.shared.evaluation import ENSEMBLE_NAME, TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import AnnouncedOddsRepository, ModelRepository
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests import synthetic_season as season
from yosou.shared.workflow import SegmentedPrediction

from ..command import CommandLine
from ..danger import BASE_OUT, DANGER, IS_DANGER, DangerJudge
from ..dataset import FAVORITE_BAND, dataset_builder
from ..repository.danger_threshold_repository import FILE_NAME as DANGER_FILE
from ..workflow import PROBABILITY, SEGMENTS, TIMINGS, PredictionWorkflow

#: 確定前の 1R（8頭登録・馬番8 は速報で取消）で、利用者が渡す人気。7頭立てなので 1〜3番人気が対象。
GIVEN_POPULARITY = ["3:1", "5:2", "1:3"]
#: 同じレースで利用者が渡す全頭の単勝オッズ（人気の順と同じ並び。前日・当日はオッズも使う）。
GIVEN_ODDS = ["3:2.2", "5:3.4", "1:4.5", "2:9.0", "4:12.0", "6:20.0", "7:30.0"]


def _workflow(con, models: Path, judges: dict | None = None) -> PredictionWorkflow:
    return PredictionWorkflow(
        dataset_builder(con), SegmentedPrediction(SEGMENTS, models),
        PopularityApplier(AnnouncedOddsRepository(con)), OddsResolver(AnnouncedOddsRepository(con)), judges or {},
    )


def test_training_saves_two_models_for_each_band_and_timing(trained):
    models, reports = trained
    expected_files = {SETTINGS_FILE, *(model_type.file_name for model_type in MEMBER_TYPES)}
    # 合成データは 13頭立て以下なので、4〜5番人気の人気馬はいない（その人気帯は学習しない）
    assert [label for label, _ in reports] == ["1番人気", "2〜3番人気"]
    for (label, report), timing in product(reports, TIMINGS):
        folder = SEGMENTS.root_of(models, label) / timing.value
        assert report.model_folders[timing] == folder
        assert {path.name for path in folder.iterdir()} == expected_files
    # 木曜は学習しない（設計書 07）
    assert not (SEGMENTS.root_of(models, "1番人気") / PredictionTiming.THURSDAY.value).exists()


def test_training_reports_validation_scores(trained):
    _, reports = trained
    report = dict(reports)["1番人気"]
    assert len(report.evaluations) == len(TIMINGS) * (len(MEMBER_TYPES) + 1)
    ensembles = [e for e in report.evaluations if e.model == ENSEMBLE_NAME]
    assert all(e.rows == len(report.split.valid) for e in ensembles)
    assert all(0.0 < e.log_loss for e in ensembles)
    # 1番人気の学習データには1番人気だけが入る
    assert set(report.split.train.evaluation[FAVORITE_BAND]) == {"1番人気"}


def test_prediction_of_a_finished_race_uses_the_final_popularity(
        season_db: Path, trained, training_data: TrainingData):
    models, _ = trained
    race_id = training_data.ids[RACE_ID].iloc[-1]
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models).run(race_id, PredictionTiming.RACE_DAY)
    # 10頭立てなので 1〜3番人気の3頭。--pops を渡さなくても、元DB の確定単勝人気で選べる
    assert prediction["人気順位"].tolist() == [1.0, 2.0, 3.0]
    member_names = [model_type.name for model_type in MEMBER_TYPES]
    np.testing.assert_allclose(prediction[PROBABILITY], prediction[member_names].mean(axis=1))
    assert prediction[PROBABILITY].between(0, 1, inclusive="neither").all()
    # 危険度は、予想の確率 − オッズから見た4着以下の確率
    np.testing.assert_allclose(prediction[DANGER], prediction[PROBABILITY] - prediction[BASE_OUT])


def test_prediction_of_a_card_needs_the_given_popularity(season_db: Path, trained):
    models, _ = trained
    given = PopularityInput.of(GIVEN_POPULARITY)
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.RACE_DAY, given,
                                                OddsInput.of(GIVEN_ODDS))
        with pytest.raises(ValueError, match="--pops"):
            _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.RACE_DAY)
    assert prediction[HORSE_NO].tolist() == [1, 3, 5]
    assert prediction["人気順位"].tolist() == [3.0, 1.0, 2.0]


def test_prediction_takes_the_popularity_from_the_given_odds(season_db: Path, trained):
    models, _ = trained
    judges = {PredictionTiming.RACE_DAY: DangerJudge({"1番人気": -1.0})}
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models, judges).run(
            season.CARD_RACE_ID, PredictionTiming.RACE_DAY, given_odds=OddsInput.of(GIVEN_ODDS))
    # --pops が無くても、オッズの小さい順（馬番 3・5・1）が 1〜3番人気になる
    assert prediction[HORSE_NO].tolist() == [1, 3, 5] and prediction["人気順位"].tolist() == [3.0, 1.0, 2.0]
    # 線を決めた人気帯（1番人気）だけ危険を判定する
    assert prediction.set_index(HORSE_NO)[IS_DANGER].to_dict() == {1: "", 3: "危険", 5: ""}


def test_prediction_is_not_offered_on_thursday(season_db: Path, trained):
    models, _ = trained
    with db.open_db(season_db) as con, pytest.raises(ValueError, match="前日・当日"):
        _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.THURSDAY)


def test_model_repository_reports_missing_models(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="train"):
        ModelRepository(tmp_path, MEMBER_TYPES).load(PredictionTiming.DAY_BEFORE)


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_predicts_a_card_with_the_given_popularity(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--pops", *GIVEN_POPULARITY, "--odds", *GIVEN_ODDS,
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 3
    assert lines[0] == (f"順位,馬番,馬名,人気順位,{FAVORITE_BAND},{BASE_OUT},{DANGER},{IS_DANGER},"
                        f"{PROBABILITY},LightGBM,CatBoost")


def test_command_reads_the_popularity_written_with_commas(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "前日", "--pops", ",".join(GIVEN_POPULARITY),
        "--odds", ",".join(GIVEN_ODDS),
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    assert code == 0 and len(capsys.readouterr().out.strip().splitlines()) == 1 + 3


def test_command_rejects_thursday(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "木曜", "--pops", *GIVEN_POPULARITY,
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "前日・当日" in capsys.readouterr().err


def test_command_reports_errors_in_one_line(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.JUMP_CARD_RACE_ID, "--timing", "当日",
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "障害レース" in capsys.readouterr().err
    assert _run_command(["predict", "--timing", "当日", "--db", str(season_db)]) == 1


def test_command_trains_and_writes_the_report(season_db: Path, fast_settings_path: Path, tmp_path: Path):
    out = tmp_path / "report.md"
    code = _run_command([
        "train", "--config", str(fast_settings_path), "--warmup-from", "2023-10-07",
        "--train-from", "2024-01-01", "--valid-from", "2024-07-01", "--test-from", "2024-10-01",
        "--db", str(season_db), "--models", str(tmp_path / "models"), "--out", str(out),
    ])
    text = out.read_text(encoding="utf-8")
    assert code == 0 and "検証データでの当たり具合" in text and "保存したモデル" in text
    assert "| ウォームアップ | 2023-10-07 | 2023-12-31 |" in text
    assert (tmp_path / "models" / "first" / "day_before" / SETTINGS_FILE).exists()
    assert not (tmp_path / "models" / "first" / "thursday").exists()
    # 危険の判定の線も、モデルと一緒に保存する
    assert "危険の判定の線" in text and (tmp_path / "models" / DANGER_FILE).exists()
