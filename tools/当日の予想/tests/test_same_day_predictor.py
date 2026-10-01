import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 合成DB import synth  # noqa: E402
from yosou.custom_binary.feature.default_registry import DefaultRegistry  # noqa: E402
from yosou.shared.tests import synthetic_season as season  # noqa: E402

import same_day_predictor  # noqa: E402
from same_day_predictor import SameDayModel, SameDayPredictor  # noqa: E402
from 当日の予想.stakes_predictor import StakesPredictor  # noqa: E402

CARD_DAY = f"{season.CARD_RACE_ID[:4]}-{season.CARD_RACE_ID[4:6]}-{season.CARD_RACE_ID[6:8]}"
#: 架空の1シーズンで、重賞「テスト記念」（6R）がある日（2024年12月の最初の土曜）。
STAKES_DAY = "2024-12-07"


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


def _models(folder: Path, *, buys_without_weight: bool) -> list[SameDayModel]:
    """1つ目は馬体重を使う（確定前のレースには馬体重が無いので、予想できずに2つ目へ回る）。"""
    return [
        SameDayModel("馬体重あり", config(folder, "with_weight", "当日", "馬齢\n斤量\n馬体重\n"), line=1.2, buys=True),
        SameDayModel("馬体重なし", config(folder, "without_weight", "前日", "馬齢\n斤量\n前走の着順\n"), line=1.2,
                     buys=buys_without_weight),
    ]


def _models_root(folder: Path) -> Path:
    """テストのモデルの置き場所（本物の reports/ には書かない）。"""
    return folder / "reports" / "特徴量と条件を選んで予想"


@pytest.fixture
def models(tmp_path) -> list[SameDayModel]:
    return _models(tmp_path, buys_without_weight=True)


@pytest.fixture
def predictor(models, season_db, tmp_path) -> SameDayPredictor:
    result = SameDayPredictor(models, DefaultRegistry().build(), season_db, line=0.0, models_root=_models_root(tmp_path))
    logs: list[str] = []
    result.ensure_models(log=logs.append)
    assert len(logs) == 2 and all((tmp_path / "reports" / "特徴量と条件を選んで予想" / name / "model.json").is_file()
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


def test_each_model_has_its_own_line_and_the_given_line_replaces_it(season_db, tmp_path):
    models = _models(tmp_path, buys_without_weight=False)
    assert SameDayPredictor(models, DefaultRegistry().build(), season_db).line_of("馬体重あり") == 1.2
    replaced = SameDayPredictor(models, DefaultRegistry().build(), season_db, line=1.5)
    assert replaced.line_of("馬体重なし") == 1.5 and not replaced.buys_with("馬体重なし")


def test_a_model_that_does_not_buy_marks_reference_and_lists_no_buys(predictor, season_db, tmp_path):
    """買わないモデル（馬体重なし）では、線に届いた馬の印を「参考」にし、買いの一覧に入れない。"""
    reference = SameDayPredictor(_models(tmp_path, buys_without_weight=False), DefaultRegistry().build(), season_db,
                                 line=0.0, models_root=_models_root(tmp_path))
    tables = reference.run(CARD_DAY, "00:00")
    # 買いの一覧には、買うモデル（馬体重あり。速報の馬体重がある 1R を予想できる）の馬だけが入り、買わないモデルの馬は入らない
    assert "馬体重なし は参考" in tables[0].title and {row[-1] for row in tables[0].rows} == {"馬体重あり"}
    races = [table for table in tables[1:] if "（馬体重なし・参考: 買わない）" in table.title]
    assert races and "買い" not in {row[-1] for row in races[0].rows}


def test_the_mark_is_buy_only_for_a_model_that_buys():
    assert same_day_predictor._mark(True, True) == "買い"
    assert same_day_predictor._mark(True, False) == "参考"
    assert same_day_predictor._mark(False, True) == "" and same_day_predictor._mark(False, False) == ""


def test_stakes_table_follows_the_stakes_race_and_leaves_buys_alone(predictor, models, season_db, tmp_path):
    """重賞の日は、重賞のレースの表のすぐ下に重賞の予想の表が並ぶ。買いの一覧と注記のレース数は変わらない。

    ここではモデルの置き場所を空にして、「モデルが無い」ときも落ちずに理由の表が出ることを確かめる
    （学習済みのモデルでの予測は test_stakes_predictor.py）。
    """
    plain = predictor.run(STAKES_DAY, "00:00")
    predictor_with_stakes = SameDayPredictor(models, DefaultRegistry().build(), season_db, 0.0,
                                             StakesPredictor(tmp_path / "no_models"), models_root=_models_root(tmp_path))
    tables = predictor_with_stakes.run(STAKES_DAY, "00:00")
    stakes = [index for index, table in enumerate(tables) if "重賞の予想" in table.title]
    assert len(stakes) == 1
    assert tables[stakes[0] - 1].title.startswith("東京6R")
    assert tables[stakes[0]].title.endswith("（予想できない）")
    assert tables[0].rows == plain[0].rows and tables[0].note == plain[0].note
    assert len(tables) == len(plain) + 1
