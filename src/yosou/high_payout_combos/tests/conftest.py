"""この予想のテストの準備。実DB は使わず、乱数で作った架空のシーズン（``synthetic_season.py``）だけを使う。

| フィクスチャ | 中身 |
|---|---|
| ``season`` | 架空の4年ぶんの組の表（ワイドと3連単）を書いたフォルダと、年ごとの馬ごとの表 |
| ``fast_settings`` | テストで速く学習が終わる設定 |
| ``samples`` | 架空のシーズン用の、外れを多めに残す間引き（行が少ないので） |
| ``walked`` | 2023年と2024年を、年ごとに学んで予測した結果（予測の置き場所と、券種ごとの結果） |
| ``trained_models`` | 本番のモデルを学習して保存したフォルダと、券種ごとの結果 |
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from yosou.shared.betting import TicketType
from yosou.shared.setting import HyperparameterSettings

from ..dataset import MissSampling
from ..repository import ComboTableRepository, PredictionStore, TicketModelRepository
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import ProductionTraining, WalkForwardWorkflow, YearSamples
from . import synthetic_season

#: テストで速く学習が終わる設定（木の数を少なく、葉の最小の行数を小さく）。初期値のファイルに重ねる。
FAST_SETTINGS = """
[lightgbm]
early_stopping_rounds = 10

[lightgbm.params]
n_estimators = 40
min_child_samples = 5
n_jobs = 1

[catboost]
early_stopping_rounds = 10

[catboost.params]
iterations = 40
depth = 3
thread_count = 1
"""
#: 予測を始める年（2023年は 2021年で学び 2022年で止める。2024年は 2021〜2022年で学び 2023年で止める）。
FIRST_TEST_YEAR = 2023


@pytest.fixture(scope="session")
def season(tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    """架空のシーズンの組の表（``tables``）と、年 → 馬ごとの表（``horses``）。"""
    tables = ComboTableRepository(tmp_path_factory.mktemp("high_payout") / "tables")
    return SimpleNamespace(tables=tables, horses=synthetic_season.write_season_tables(tables))


@pytest.fixture(scope="session")
def fast_settings(tmp_path_factory: pytest.TempPathFactory) -> HyperparameterSettings:
    path = tmp_path_factory.mktemp("high_payout_settings") / "fast.toml"
    path.write_text(FAST_SETTINGS, encoding="utf-8", newline="\n")
    return HyperparameterSettings.load(path, defaults=DEFAULT_SETTINGS_PATH)


@pytest.fixture(scope="session")
def samples(season: SimpleNamespace) -> YearSamples:
    keep_rates = {TicketType.WIDE: 0.8, TicketType.TRIFECTA: 0.3}
    return YearSamples(season.tables, MissSampling(keep_rates))


@pytest.fixture(scope="session")
def walked(season: SimpleNamespace, fast_settings: HyperparameterSettings, samples: YearSamples,
           tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    """年ごとに学んで予測した結果。``store`` は予測の置き場所、``results`` は券種 → 年ごとの結果。"""
    store = PredictionStore(tmp_path_factory.mktemp("high_payout_predictions"))
    workflow = WalkForwardWorkflow(season.tables, store, fast_settings, samples)
    results = {ticket_type: workflow.run(ticket_type, FIRST_TEST_YEAR) for ticket_type in synthetic_season.TRAINED_TYPES}
    return SimpleNamespace(store=store, results=results)


@pytest.fixture(scope="session")
def trained_models(season: SimpleNamespace, fast_settings: HyperparameterSettings, samples: YearSamples,
                   tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    """本番のモデル。``folder`` はモデルの置き場所、``results`` は券種 → 結果。"""
    folder = tmp_path_factory.mktemp("high_payout_models")
    training = ProductionTraining(season.tables, TicketModelRepository(folder), fast_settings, samples)
    results = {ticket_type: training.run(ticket_type) for ticket_type in synthetic_season.TRAINED_TYPES}
    return SimpleNamespace(folder=folder, results=results)
