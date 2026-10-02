"""重賞の日に、一般の予想「近走と適性から3着以内を予想」の当日の予測を、重賞の表にする部品（合成DB だけを使う）。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402
from 合成DB import synth  # noqa: E402
from yosou.form_aptitude_top3.command import CommandLine  # noqa: E402
from yosou.shared.tests import synthetic_season as season  # noqa: E402
from yosou.shared.tests.synthetic_season.season_plan import FIELD_SIZE  # noqa: E402

from 当日の予想.form_race_day_table import FormRaceDayTable  # noqa: E402
from 当日の予想.stakes_predictor import StakesPredictor  # noqa: E402

#: 架空の1シーズンの重賞「テスト記念」（G3・6R）の、終わった開催（2024年12月の最初の土曜）と、同じ日の平場の 1R。
STAKES_RACE = {"rid": "2024120705010106", "場": "東京", "R": 6, "発走": "20:05", "レース名": "テスト記念"}
FLAT_RACE = {"rid": "2024120705010101", "場": "東京", "R": 1, "発走": "13:40", "レース名": ""}
#: 合成のシーズンで数秒で学習が終わる設定。
FAST_SETTINGS = """
[lightgbm]
early_stopping_rounds = 5
min_category_count = 20

[lightgbm.params]
n_estimators = 20
min_child_samples = 20

[catboost]
early_stopping_rounds = 5

[catboost.params]
iterations = 20
depth = 3
"""


@pytest.fixture(scope="module")
def season_db(tmp_path_factory) -> Path:
    return synth.build_db(tmp_path_factory.mktemp("stakes_season") / "season.duckdb", season.SeasonBuilder().build())


@pytest.fixture(scope="module")
def figure_cache(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("figures")


@pytest.fixture(scope="module")
def form_models(season_db, figure_cache, tmp_path_factory) -> Path:
    """一般の予想（近走と適性）を、架空の1シーズンで train コマンドどおりに学習したモデルの置き場所。"""
    folder = tmp_path_factory.mktemp("form_models")
    settings = folder / "fast.toml"
    settings.write_text(FAST_SETTINGS, encoding="utf-8")
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run([
            "train", "--config", str(settings), "--warmup-from", season.FIRST_RACE_DAY.isoformat(),
            "--train-from", season.TRAIN_FIRST_DAY.isoformat(), "--ability-train-from", season.TRAIN_FIRST_DAY.isoformat(),
            "--valid-from", season.VALID_FIRST_DAY.isoformat(), "--test-from", season.TEST_FIRST_DAY.isoformat(),
            "--figure-cache", str(figure_cache), "--db", str(season_db), "--models", str(folder / "models"),
            "--out", str(folder / "report.md"),
        ])
    assert stopped.value.code == 0
    return folder / "models"


def test_stakes_race_gets_the_general_prediction_table(season_db, form_models, figure_cache):
    with db.open_db(season_db) as con:
        tables = StakesPredictor(FormRaceDayTable(form_models, figure_cache)).tables(con, STAKES_RACE)
    assert len(tables) == 1
    table = tables[0]
    # 見出しに、一般の予想の当日の予測であることを書く
    assert "テスト記念（G3）: 重賞の予想（一般の予想「近走と適性から3着以内を予想」の当日）" in table.title
    assert "買い" in table.note and "引退" in table.note  # 買いの判断に使っていないことと、専用モデルの引退を書く
    assert len(table.rows) == FIELD_SIZE
    assert table.columns[:3] == ["順位", "馬番", "馬名"]


def test_flat_race_gets_nothing(season_db, form_models, figure_cache):
    with db.open_db(season_db) as con:
        assert StakesPredictor(FormRaceDayTable(form_models, figure_cache)).tables(con, FLAT_RACE) == []


def test_missing_models_are_reported_without_failing(season_db, tmp_path):
    with db.open_db(season_db) as con:
        tables = StakesPredictor(FormRaceDayTable(tmp_path / "no_models", tmp_path)).tables(con, STAKES_RACE)
    assert len(tables) == 1 and tables[0].title.endswith("（予想できない）")
    assert "yosou.form_aptitude_top3 train" in tables[0].rows[0][0]
