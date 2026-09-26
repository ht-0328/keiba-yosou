"""学習したモデルを保存して読み、確定前のレースを予測できるかを確かめる（合成DB）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings
from yosou.shared.tests.synthetic_season import CARD_RACE_ID

from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import DevelopmentModelKind, DevelopmentPredictionWorkflow, ForecastGroup, GroupFitter, KindModelStore
from .conftest import EARLY_PERIOD, FINISH_PERIOD, LATE_PERIOD


@pytest.fixture(scope="module")
def models(datasets, fast_settings_path: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """当日の時点の3つの組のモデルを学習して保存したフォルダ。"""
    root = tmp_path_factory.mktemp("models")
    store = KindModelStore(root)
    settings = HyperparameterSettings.load(fast_settings_path, defaults=DEFAULT_SETTINGS_PATH)
    timing = PredictionTiming.RACE_DAY

    def sink(kind, members, order_lambda):
        store.save(kind, timing, members, settings, order_lambda)

    fitter = GroupFitter()
    early = fitter.fit_predict(ForecastGroup.EARLY, EARLY_PERIOD, datasets, None, None, timing, settings, sink)
    late = fitter.fit_predict(ForecastGroup.LATE, LATE_PERIOD, datasets, early, None, timing, settings, sink)
    fitter.fit_predict(ForecastGroup.FINISH, FINISH_PERIOD, datasets, early, late, timing, settings, sink)
    return root


def test_saved_models_can_be_read_back(models: Path) -> None:
    store = KindModelStore(models)
    assert len(store.load(DevelopmentModelKind.FINISH, PredictionTiming.RACE_DAY)) == 2
    assert 0.5 <= store.load_lambda(PredictionTiming.RACE_DAY) <= 1.0


def test_card_race_is_predicted_with_marks_and_tickets(models: Path, development_db: Path, tmp_path: Path) -> None:
    workflow = DevelopmentPredictionWorkflow(models, tmp_path / "predictions", development_db)
    forecast = workflow.run(CARD_RACE_ID, PredictionTiming.RACE_DAY)
    horses = forecast.horses
    assert np.isclose(horses["1着の確率"].sum(), 1.0)
    assert np.isclose(horses["3着以内の確率"].sum(), 3.0)
    assert horses["印"].iloc[0] == "◎"
    assert set(forecast.tickets["券種"]) == {"単勝", "複勝", "ワイド", "馬連", "馬単", "3連複", "3連単"}
    assert list((tmp_path / "predictions").rglob("*.pkl"))
