"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う。

合成DB（``season_db``）・速い設定（``fast_settings_path``）・期間（``season_period``）は
``src/yosou/conftest.py``。ここには、この予想の組み立てで作るものを置く。

| フィクスチャ | 中身 |
|---|---|
| ``training_data`` | 今の材料の学習データ（出走した全頭・3着以内・特徴量 79個） |
| ``figure_cache`` | スピード指数をとっておく一時フォルダ（本物の ``reports/能力指数/cache/`` を書き換えない） |
| ``ability_training_data`` | 馬の力の材料の学習データ（M の 202個と J の4個） |
| ``development_root`` | 予想「展開から着順を予想」の置き場所の代わり（木曜の、架空の前半・後半の年ごとの予測だけを置いた一時フォルダ） |
| ``trained`` | 本番と同じ学習（train コマンド）を1回通した結果（モデルを置いたフォルダと、学習の報告の文章） |
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from 共通 import db

from yosou.race_development.feature import GroupForecast
from yosou.race_development.repository import OutOfSampleRepository
from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData, TrainingPeriod
from yosou.shared.feature import PredictionTiming
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..dataset import ability_dataset_builder, dataset_builder


@pytest.fixture(scope="session")
def training_data(season_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンの学習データ（今の材料）。"""
    with db.open_db(season_db) as con:
        return dataset_builder(con).build_training_data(season_period)


@pytest.fixture(scope="session")
def figure_cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """スピード指数をとっておく一時フォルダ。"""
    return tmp_path_factory.mktemp("figures")


@pytest.fixture(scope="session")
def ability_training_data(season_db: Path, season_period: TrainingPeriod, figure_cache: Path) -> TrainingData:
    """架空の1シーズンの学習データ（馬の力の材料）。"""
    with db.open_db(season_db) as con:
        return ability_dataset_builder(con, figure_cache).build_training_data(season_period)


@pytest.fixture(scope="session")
def development_root(ability_training_data: TrainingData, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """展開の予想の置き場所の代わり。学習データの出走ごとに、乱数で作った木曜の前半・後半の予測を、年ごとの確かめの形で置く。"""
    root = tmp_path_factory.mktemp("development")
    rng = np.random.default_rng(20261002)
    ids = ability_training_data.ids[[RACE_ID, HORSE_ID]].astype(str).reset_index(drop=True)
    races = ids[[RACE_ID]].drop_duplicates().reset_index(drop=True)
    early = GroupForecast(ids.assign(p_leader=rng.uniform(size=len(ids)), p_front=rng.uniform(size=len(ids)),
                                     p_middle=0.3, p_back=0.2),
                          races.assign(p_slow=0.3, p_even=0.4, p_high=0.3, first_q10=-1.0,
                                       first_q50=rng.normal(size=len(races)), first_q90=1.0))
    late = GroupForecast(ids.assign(corner4_pred=rng.uniform(size=len(ids)), closing_pred=rng.uniform(size=len(ids))),
                         races.assign(second_q10=-1.0, second_q50=rng.normal(size=len(races)), second_q90=1.0))
    repository = OutOfSampleRepository(root / "out_of_sample")
    repository.save("early", PredictionTiming.THURSDAY, 2024, "テスト", early)
    repository.save("late", PredictionTiming.THURSDAY, 2024, "テスト", late)
    return root


@pytest.fixture(scope="session")
def trained(season_db: Path, fast_settings_path: Path, figure_cache: Path, development_root: Path,
            tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """train コマンドを1回通して、モデルを置いたフォルダと、学習の報告（Markdown）を返す。

    期間は架空の1シーズンに合わせる（馬の力の材料も、今の材料と同じ 2024-01-01 から学ぶ）。
    """
    folder = tmp_path_factory.mktemp("trained")
    models, out = folder / "models", folder / "report.md"
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run([
            "train", "--config", str(fast_settings_path), "--warmup-from", season.FIRST_RACE_DAY.isoformat(),
            "--train-from", season.TRAIN_FIRST_DAY.isoformat(), "--ability-train-from", season.TRAIN_FIRST_DAY.isoformat(),
            "--valid-from", season.VALID_FIRST_DAY.isoformat(), "--test-from", season.TEST_FIRST_DAY.isoformat(),
            "--figure-cache", str(figure_cache), "--development-root", str(development_root),
            "--db", str(season_db), "--models", str(models), "--out", str(out),
        ])
    assert stopped.value.code == 0
    return models, out.read_text(encoding="utf-8")
