"""重賞の日に、予想モデル「重賞の傾向と近走から3着以内を予想」の予測を表にする部品（合成DB だけを使う）。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402
from 合成DB import synth  # noqa: E402
from yosou.shared.command import PlacePriceStep  # noqa: E402
from yosou.shared.dataset import TrainingPeriod  # noqa: E402
from yosou.shared.ml_model import MEMBER_TYPES  # noqa: E402
from yosou.shared.repository import ModelRepository  # noqa: E402
from yosou.shared.tests import synthetic_season as season  # noqa: E402
from yosou.shared.tests.synthetic_season.season_plan import FIELD_SIZE  # noqa: E402
from yosou.shared.workflow import TrainingWorkflow  # noqa: E402
from yosou.stakes_tendency_top3.dataset import dataset_builder  # noqa: E402
from yosou.stakes_tendency_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.stakes_tendency_top3.workflow import TIMINGS  # noqa: E402

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
def stakes_models(season_db, tmp_path_factory) -> Path:
    """重賞の予想を、架空の1シーズンで3つの時点ぶん学習したモデルの置き場所。"""
    folder = tmp_path_factory.mktemp("stakes_models")
    settings = folder / "fast.toml"
    settings.write_text(FAST_SETTINGS, encoding="utf-8")
    period = TrainingPeriod(season.FIRST_RACE_DAY, season.TRAIN_FIRST_DAY, season.VALID_FIRST_DAY, season.TEST_FIRST_DAY)
    with db.open_db(season_db) as con:
        workflow = TrainingWorkflow(dataset_builder(con), period, ModelRepository(folder, MEMBER_TYPES),
                                    TIMINGS, DEFAULT_SETTINGS_PATH)
        report = workflow.run(settings)
    PlacePriceStep().run(report.split.train, folder)
    return folder


def test_stakes_race_gets_the_prediction_table(season_db, stakes_models):
    with db.open_db(season_db) as con:
        tables = StakesPredictor(stakes_models).tables(con, STAKES_RACE)
    assert len(tables) == 1
    table = tables[0]
    assert "テスト記念（G3）: 重賞の予想" in table.title
    assert "買い" in table.note  # 買いの判断に使っていないことを書く
    assert len(table.rows) == FIELD_SIZE
    assert table.columns[:3] == ["順位", "馬番", "馬名"]


def test_flat_race_gets_nothing(season_db, stakes_models):
    with db.open_db(season_db) as con:
        assert StakesPredictor(stakes_models).tables(con, FLAT_RACE) == []


def test_missing_models_are_reported_without_failing(season_db, tmp_path):
    with db.open_db(season_db) as con:
        tables = StakesPredictor(tmp_path / "no_models").tables(con, STAKES_RACE)
    assert len(tables) == 1 and tables[0].title.endswith("（予想できない）")
    assert "train" in tables[0].rows[0][0]
