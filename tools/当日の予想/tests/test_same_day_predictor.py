import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 合成DB import synth  # noqa: E402
from yosou.custom_binary import workflow  # noqa: E402
from yosou.custom_binary.feature.registrations import default_registry  # noqa: E402
from yosou.shared.tests import synthetic_season as season  # noqa: E402

from same_day_predictor import SameDayModel, SameDayPredictor  # noqa: E402

CARD_DAY = f"{season.CARD_RACE_ID[:4]}-{season.CARD_RACE_ID[4:6]}-{season.CARD_RACE_ID[6:8]}"


@pytest.fixture(scope="module")
def season_db(tmp_path_factory) -> Path:
    return synth.build_db(tmp_path_factory.mktemp("season") / "season.duckdb", season.SeasonBuilder().build())


def config(folder: Path, name: str, timing: str, features: str) -> Path:
    """合成のシーズンで数秒で学習できる、小さな設定。"""
    (folder / f"{name}.txt").write_text(features, encoding="utf-8")
    path = folder / f"{name}.yml"
    path.write_text(f"""name: {name}
features_file: {name}.txt
target: 馬券内
timing: {timing}
training:
  warmup_from: {season.FIRST_RACE_DAY.isoformat()}
  train_from: {season.TRAIN_FIRST_DAY.isoformat()}
  valid_from: {season.VALID_FIRST_DAY.isoformat()}
  test_from: {season.TEST_FIRST_DAY.isoformat()}
lightgbm: {{early_stopping_rounds: 3, min_category_count: 2, params: {{n_estimators: 8, min_child_samples: 5}}}}
catboost: {{early_stopping_rounds: 3, params: {{iterations: 8, depth: 3}}}}
""", encoding="utf-8")
    return path


@pytest.fixture
def predictor(season_db, tmp_path, monkeypatch) -> SameDayPredictor:
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    models = [
        # 1つ目は馬体重を使う（確定前のレースには馬体重が無いので、予想できずに2つ目へ回る）。
        SameDayModel("馬体重あり", config(tmp_path, "with_weight", "当日", "馬齢\n斤量\n馬体重\n")),
        SameDayModel("馬体重なし", config(tmp_path, "without_weight", "前日", "馬齢\n斤量\n前走の着順\n")),
    ]
    result = SameDayPredictor(models, default_registry(), season_db, line=0.0)
    logs: list[str] = []
    result.ensure_models(log=logs.append)
    assert len(logs) == 2 and all((tmp_path / "reports" / "custom_binary" / name / "model.json").is_file()
                                  for name in ("with_weight", "without_weight"))
    return result


def test_falls_back_to_the_next_model_and_lists_buys_first(predictor):
    tables = predictor.run(CARD_DAY, "00:00")
    assert tables[0].title.startswith("買い")
    races = [table for table in tables[1:] if "（馬体重なし）" in table.title]
    assert races, [table.title for table in tables]
    assert races[0].columns[:3] == ["馬番", "馬名", "人気"]


def test_races_before_the_given_time_are_skipped(predictor):
    tables = predictor.run(CARD_DAY, "23:59")
    assert len(tables) == 1 and tables[0].rows == []


def test_models_are_trained_only_once(predictor):
    logs: list[str] = []
    predictor.ensure_models(log=logs.append)
    assert logs == []
