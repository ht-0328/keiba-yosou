"""学習の流れ（設計書 05 の図1）と予測の流れ（図2）、モデルの保存と読み込み、コマンドの入口。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from 共通 import db

from yosou.shared.dataset import (
    HORSE_NO,
    RACE_ID,
    PopularityApplier,
    PopularityInput,
    RaceRecordsLoader,
    TrainingData,
)
from yosou.shared.evaluation import ENSEMBLE_NAME, TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.repository import AnnouncedOddsRepository, ModelRepository
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..dataset import LONGSHOT_ZONE, LongshotZone, LongshotZoneFilter, dataset_builder
from ..workflow import PROBABILITY, TIMINGS, PredictionWorkflow

#: 確定前の 1R（8頭登録・馬番8 は速報で取消）で、利用者が渡す全頭の人気。7頭立てなので 4番人気以下が穴馬。
GIVEN_POPULARITY = ["3:1", "5:2", "1:3", "2:4", "4:5", "6:6", "7:7"]
#: その穴馬の馬番（4〜7番人気）と区分（4〜6番人気が中穴、7番人気が大穴）。
LONGSHOT_HORSE_NOS = [2, 4, 6, 7]
MID, BIG = LongshotZone.MID.label, LongshotZone.BIG.label


def _workflow(con, models: Path) -> PredictionWorkflow:
    return PredictionWorkflow(
        dataset_builder(con), ModelRepository(models, MEMBER_TYPES),
        PopularityApplier(AnnouncedOddsRepository(con)), LongshotZoneFilter(),
    )


def _thursday_popularity(con) -> list[str]:
    """木曜の 2R（出走馬名表。馬番が未定）の全頭に、馬名で見立ての人気を付ける。"""
    names = RaceRecordsLoader(con).load(season.ENTRY_LIST_RACE_ID).entries["horse_name"].tolist()
    return [f"{name}:{rank}" for rank, name in enumerate(names, start=1)]


def test_training_saves_two_models_for_each_of_the_three_timings(trained: tuple[Path, TrainingReport]):
    models, report = trained
    expected_files = {SETTINGS_FILE, *(model_type.file_name for model_type in MEMBER_TYPES)}
    assert set(report.model_folders) == set(TIMINGS) == set(PredictionTiming)
    for timing in TIMINGS:
        folder = models / timing.value
        assert report.model_folders[timing] == folder
        assert {path.name for path in folder.iterdir()} == expected_files


def test_training_reports_validation_scores(trained: tuple[Path, TrainingReport]):
    _, report = trained
    assert len(report.evaluations) == len(TIMINGS) * (len(MEMBER_TYPES) + 1)
    ensembles = [e for e in report.evaluations if e.model == ENSEMBLE_NAME]
    assert all(e.rows == len(report.split.valid) for e in ensembles)
    assert all(0.0 < e.log_loss for e in ensembles)


def test_prediction_of_a_finished_race_uses_the_final_popularity(
        season_db: Path, trained: tuple[Path, TrainingReport], training_data: TrainingData):
    models, _ = trained
    race_id = training_data.ids[RACE_ID].iloc[-1]
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models).run(race_id, PredictionTiming.RACE_DAY)
    # 10頭立て（取消があれば 9頭）なので 4番人気以下。--pops を渡さなくても、元DB の確定単勝人気で選べる
    ranks = sorted(prediction["人気順位"].tolist())
    assert ranks == list(range(4, 4 + len(ranks))) and len(ranks) >= 6
    assert set(prediction[LONGSHOT_ZONE]) == {MID, BIG}
    member_names = [model_type.name for model_type in MEMBER_TYPES]
    np.testing.assert_allclose(prediction[PROBABILITY], prediction[member_names].mean(axis=1))
    assert prediction[PROBABILITY].between(0, 1, inclusive="neither").all()


def test_prediction_of_a_card_needs_the_popularity_of_every_runner(season_db: Path, trained):
    models, _ = trained
    given = PopularityInput.of(GIVEN_POPULARITY)
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.RACE_DAY, given)
        with pytest.raises(ValueError, match="--pops"):
            _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.RACE_DAY)
        with pytest.raises(ValueError, match="4頭います"):
            # 人気馬の3頭だけ渡しても、残りの馬の人気が分からないので止まる
            _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.RACE_DAY,
                                       PopularityInput.of(GIVEN_POPULARITY[:3]))
    assert prediction[HORSE_NO].tolist() == LONGSHOT_HORSE_NOS
    assert prediction["人気順位"].tolist() == [4.0, 5.0, 6.0, 7.0]
    assert prediction[LONGSHOT_ZONE].tolist() == [MID, MID, MID, BIG]


def test_prediction_can_be_narrowed_to_a_zone(season_db: Path, trained):
    models, _ = trained
    given = PopularityInput.of(GIVEN_POPULARITY)
    with db.open_db(season_db) as con:
        mid = _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.DAY_BEFORE, given, LongshotZone.MID)
        big = _workflow(con, models).run(season.CARD_RACE_ID, PredictionTiming.DAY_BEFORE, given, LongshotZone.BIG)
    assert mid[HORSE_NO].tolist() == [2, 4, 6] and big[HORSE_NO].tolist() == [7]


def test_prediction_on_thursday_takes_the_popularity_by_horse_name(season_db: Path, trained):
    models, _ = trained
    with db.open_db(season_db) as con:
        given = PopularityInput.of(_thursday_popularity(con))
        prediction = _workflow(con, models).run(season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY, given)
        with pytest.raises(ValueError, match="--pops"):
            _workflow(con, models).run(season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY)
    # 8頭立てなので 4番人気以下の5頭。馬番はまだ無い。区分は 4〜6番人気が中穴、7・8番人気が大穴
    assert len(prediction) == 5 and prediction[HORSE_NO].isna().all()
    assert sorted(prediction["人気順位"].tolist()) == [4.0, 5.0, 6.0, 7.0, 8.0]
    assert sorted(prediction[LONGSHOT_ZONE].tolist()) == [MID] * 3 + [BIG] * 2


def test_model_repository_reports_missing_models(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="train"):
        ModelRepository(tmp_path, MEMBER_TYPES).load(PredictionTiming.THURSDAY)


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_predicts_a_card_with_the_given_popularity(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--pops", *GIVEN_POPULARITY,
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + len(LONGSHOT_HORSE_NOS)
    assert lines[0] == f"順位,馬番,馬名,人気順位,{LONGSHOT_ZONE},{PROBABILITY},LightGBM,CatBoost"


def test_command_narrows_the_output_by_zone(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "前日", "--pops", ",".join(GIVEN_POPULARITY),
        "--zone", "大穴", "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 1 and f",{BIG}," in lines[1]


def test_command_predicts_on_thursday_by_horse_names(season_db: Path, trained, capsys):
    models, _ = trained
    with db.open_db(season_db) as con:
        given = _thursday_popularity(con)
    code = _run_command([
        "predict", season.ENTRY_LIST_RACE_ID, "--timing", "木曜", "--pops", *given,
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 5
    # 馬番はまだ無いので空欄
    assert all(line.split(",")[1] == "" for line in lines[1:])


def test_command_reports_an_unknown_horse_name(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.ENTRY_LIST_RACE_ID, "--timing", "木曜", "--pops", "いない馬:1",
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "馬名 いない馬 はこのレースにいません" in capsys.readouterr().err


def test_command_rejects_an_unknown_zone(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--zone", "超大穴",
        "--db", str(season_db), "--models", str(models),
    ])
    assert code != 0 and "超大穴" in capsys.readouterr().err


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
    for timing in PredictionTiming:
        assert (tmp_path / "models" / timing.value / SETTINGS_FILE).exists()
