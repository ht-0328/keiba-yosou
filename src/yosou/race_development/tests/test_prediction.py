"""学習したモデルを保存して読み、確定前のレースを予測できるかを確かめる（合成DB）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from 共通 import db

from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings
from yosou.shared.tests.synthetic_season import CARD_RACE_ID

from yosou.shared.dataset import OddsInput
from yosou.shared.feature.pace_forecast import SOURCE_COLUMNS
from yosou.shared.feature.pace_forecast import pace_forecast_columns as pace_names

from ..feature import PriorForecasts
from ..setting import DEFAULT_SETTINGS_PATH
from ..tendency import TendencyModelStore, TendencySource
from ..workflow import (
    DevelopmentModelKind,
    DevelopmentPaceWorkflow,
    DevelopmentPredictionWorkflow,
    ForecastGroup,
    GroupFitter,
    KindModelStore,
)
from .conftest import EARLY_PERIOD, FINISH_PERIOD, LATE_PERIOD, TENDENCY_PERIOD

#: 出馬表のレースに手で渡す単勝オッズ（合成DB には、締め切り前のオッズが無いため。``--odds`` の書き方）。
CARD_ODDS = OddsInput.of([f"{horse_no}:{1.5 + horse_no}" for horse_no in range(1, 9)])


@pytest.fixture(scope="module")
def models(datasets, fast_settings_path: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """当日の時点の4つの組のモデル（傾向の組は既存の予想のモデル）を学習して保存したフォルダ。"""
    root = tmp_path_factory.mktemp("models")
    store, tendency_store = KindModelStore(root), TendencyModelStore(root)
    settings = HyperparameterSettings.load(fast_settings_path, defaults=DEFAULT_SETTINGS_PATH)
    timing = PredictionTiming.RACE_DAY

    def sink(kind, members, order_lambda):
        store.save(kind, timing, members, settings, order_lambda)

    def tendency_sink(source, unit, members):
        tendency_store.save(source, unit, timing, members, settings)

    fitter = GroupFitter()
    tendency = fitter.fit_predict(ForecastGroup.TENDENCY, TENDENCY_PERIOD, datasets, PriorForecasts(), timing, settings,
                                  sink, tendency_sink)
    priors = PriorForecasts(tendency)
    priors = priors.with_early(fitter.fit_predict(ForecastGroup.EARLY, EARLY_PERIOD, datasets, priors, timing, settings, sink))
    priors = priors.with_late(fitter.fit_predict(ForecastGroup.LATE, LATE_PERIOD, datasets, priors, timing, settings, sink))
    fitter.fit_predict(ForecastGroup.FINISH, FINISH_PERIOD, datasets, priors, timing, settings, sink)
    return root


def test_saved_models_can_be_read_back(models: Path) -> None:
    store = KindModelStore(models)
    assert len(store.load(DevelopmentModelKind.FINISH, PredictionTiming.RACE_DAY)) == 2
    assert 0.5 <= store.load_lambda(PredictionTiming.RACE_DAY) <= 1.0
    tendency = TendencyModelStore(models)
    for source in (TendencySource.FORM_TOP3, TendencySource.UPSET_LEVEL):
        for unit in source.spec.units:
            assert len(tendency.load(source, unit, PredictionTiming.RACE_DAY)) == 2


def test_card_race_is_predicted_with_marks_and_tickets(models: Path, development_db: Path, tmp_path: Path) -> None:
    workflow = DevelopmentPredictionWorkflow(models, tmp_path / "predictions", development_db)
    forecast = workflow.run(CARD_RACE_ID, PredictionTiming.RACE_DAY, CARD_ODDS)
    horses = forecast.horses
    assert np.isclose(horses["1着の確率"].sum(), 1.0)
    assert np.isclose(horses["3着以内の確率"].sum(), 3.0)
    assert horses["印"].iloc[0] == "◎"
    assert horses["既存の予想の3着以内の確率"].between(0, 1).all()
    assert forecast.race["大荒れ以上の確率（単勝）"].between(0, 1).all()
    assert set(forecast.tickets["券種"]) == {"単勝", "複勝", "ワイド", "馬連", "馬単", "3連複", "3連単"}
    assert list((tmp_path / "predictions").rglob("*.pkl"))


def test_pace_workflow_gives_the_early_and_late_forecasts_for_other_models(models: Path, development_db: Path) -> None:
    with db.open_db(development_db) as con:
        table = DevelopmentPaceWorkflow(models).run(con, CARD_RACE_ID, PredictionTiming.RACE_DAY, CARD_ODDS)
    # 近走と適性の予想のまとまり P の元の予測の表。出走する全頭の行に、前半・後半の予測がそろう
    assert list(table.columns) == [*pace_names.KEY, *SOURCE_COLUMNS] and len(table) == 7
    assert table[list(SOURCE_COLUMNS)].notna().all().all()
    assert np.isclose(table[pace_names.LEADER].sum(), 1.0)
