"""学習の流れ（設計書 05 の図1）と予測の流れ（図2）、モデルの保存と読み込み、コマンドの入口。"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from 共通 import db

from yosou.shared.dataset import HORSE_NO
from yosou.shared.evaluation import ENSEMBLE_NAME
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP3_RATE
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE, PlacePriceEstimator, PlaceValueColumns
from yosou.shared.repository import AnnouncedOddsRepository, ModelRepository
from yosou.shared.repository.place_price_repository import FILE_NAME as PLACE_PRICE_FILE
from yosou.shared.workflow import AVERAGE, ModelSegments, SegmentedPrediction, TrainingWorkflow
from yosou.shared.repository.model_repository import SETTINGS_FILE
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine, predict_command
from ..dataset import (
    OddsInput,
    OddsResolver,
    PoolAvailability,
    PoolFreeData,
    ability_dataset_builder,
    race_day_dataset_builder,
)
from ..feature import WIN_ODDS
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import FORM_TIMINGS, POOL_FREE_FOLDER, PROBABILITY, PredictionWorkflow
from .test_dataset_builder import CARD_ODDS

#: 出馬表のレースに手で渡す単勝オッズ（``--odds`` の書き方）。
CARD_ODDS_TEXTS = [f"{horse_no}:{odds}" for horse_no, odds in CARD_ODDS.items()]


def test_training_saves_two_models_for_each_timing(trained: tuple[Path, str]):
    models, _ = trained
    expected_files = {SETTINGS_FILE, *(model_type.file_name for model_type in MEMBER_TYPES)}
    for timing in PredictionTiming:
        assert {path.name for path in (models / timing.value).iterdir()} == expected_files
    # 当日に券種のオッズが無いレースのための、券種の支持を使わないモデルも置く
    assert {path.name for path in (models / POOL_FREE_FOLDER / "race_day").iterdir()} == expected_files


def test_training_saves_the_settings_it_used(trained: tuple[Path, str]):
    models, _ = trained
    saved = json.loads((models / "race_day" / SETTINGS_FILE).read_text(encoding="utf-8"))
    # テスト用の設定ファイルに書いた値と、書かなかった項目の初期値
    assert saved["lightgbm"]["params"]["n_estimators"] == 60
    assert saved["lightgbm"]["params"]["num_leaves"] == 31


def test_training_reports_each_model_group(trained: tuple[Path, str]):
    _, text = trained
    # 当日（今の材料・券種の支持・馬の力の材料）・券種オッズなし（当日）・馬の力の材料（前日）・展開の予想を足した馬の力の材料（木曜）の
    # 4つの学習の結果を出す
    for subject in ("今の材料", "券種オッズなし", "馬の力の材料", "馬の力の材料 ＋ 展開の予想（木曜）"):
        assert f"{subject}: 検証データでの当たり具合" in text and f"{subject}: 保存したモデル" in text
    assert "| ウォームアップ | 2023-10-07 | 2023-12-31 |" in text
    assert "複勝の見込みの倍率" in text


def test_form_training_reports_validation_scores(season_db: Path, fast_settings_path: Path,
                                                 season_period, tmp_path: Path, figure_cache: Path):
    with db.open_db(season_db) as con:
        workflow = TrainingWorkflow(race_day_dataset_builder(con, figure_cache), season_period,
                                    ModelRepository(tmp_path, MEMBER_TYPES),
                                    FORM_TIMINGS, DEFAULT_SETTINGS_PATH)
        report = workflow.run(fast_settings_path)
    assert len(report.evaluations) == len(FORM_TIMINGS) * (len(MEMBER_TYPES) + 1)
    ensembles = [e for e in report.evaluations if e.model == ENSEMBLE_NAME]
    # 合成のシーズンは能力の高い馬が上位に来やすいので、でたらめ（AUC 0.5）よりはっきり当たる
    assert all(e.auc > 0.65 and e.rows == len(report.split.valid) for e in ensembles)
    assert all(e.tree_count is None for e in ensembles)


def test_model_repository_reports_missing_models(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="train"):
        ModelRepository(tmp_path, MEMBER_TYPES).load(PredictionTiming.RACE_DAY)


def _workflow(con: duckdb.DuckDBPyConnection, models: Path, figure_cache: Path,
              place_price: PlacePriceEstimator | None = None) -> PredictionWorkflow:
    """当日の予測の流れ（今の材料・券種の支持・馬の力の材料。当日に券種のオッズが無ければ、券種の支持を使わないモデルに切り替える）。"""
    return PredictionWorkflow(
        race_day_dataset_builder(con, figure_cache), SegmentedPrediction(ModelSegments(), models),
        OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(place_price),
        pool_free=SegmentedPrediction(ModelSegments(), models / POOL_FREE_FOLDER),
    )


def _thursday_workflow(con: duckdb.DuckDBPyConnection, models: Path, figure_cache: Path,
                       asked: list[tuple[str, PredictionTiming]]) -> PredictionWorkflow:
    """木曜の予測の流れ（馬の力の材料と展開の予想の結果）。展開の予測は、聞かれたレースと時点を ``asked`` に書き足し、
    予測の無い表を返す（展開のモデルは合成DB では学べないため。P は欠損値になる）。"""
    def pace(race_id: str, timing: PredictionTiming, given) -> pd.DataFrame:
        asked.append((race_id, timing))
        return pd.DataFrame()
    return PredictionWorkflow(
        ability_dataset_builder(con, figure_cache), SegmentedPrediction(ModelSegments(), models),
        OddsResolver(AnnouncedOddsRepository(con)), PlaceValueColumns(None), pace=pace,
    )


def test_prediction_averages_the_two_models(season_db: Path, trained: tuple[Path, str], figure_cache: Path):
    models, _ = trained
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models, figure_cache).run(
            season.CARD_RACE_ID, PredictionTiming.RACE_DAY, OddsInput.of(CARD_ODDS_TEXTS))
    assert len(prediction) == 7 and season.SCRATCHED_HORSE_NO not in set(prediction[HORSE_NO])
    member_names = [model_type.name for model_type in MEMBER_TYPES]
    np.testing.assert_allclose(prediction[PROBABILITY], prediction[member_names].mean(axis=1))
    assert prediction[PROBABILITY].between(0, 1, inclusive="neither").all()
    # 渡したオッズが、結果の表にそのまま出る
    shown = prediction.set_index(HORSE_NO)[WIN_ODDS].to_dict()
    assert shown == {horse_no: CARD_ODDS[horse_no] for horse_no in range(1, 8)}


def test_thursday_prediction_has_no_odds_column(season_db: Path, trained: tuple[Path, str], figure_cache: Path):
    models, _ = trained
    with db.open_db(season_db) as con:
        asked: list[tuple[str, PredictionTiming]] = []
        workflow = _thursday_workflow(con, models, figure_cache, asked)
        prediction = workflow.run(season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY)
    assert len(prediction) == 8 and WIN_ODDS not in prediction.columns
    # 木曜のモデルは展開の予想の結果（P）を足して学んだので、そのレースの木曜の展開の予測を聞く
    assert asked == [(season.ENTRY_LIST_RACE_ID, PredictionTiming.THURSDAY)]
    # 木曜はオッズが無いので、オッズから見た3着以内率と複勝の期待値も出さない
    assert TOP3_RATE not in prediction.columns and PLACE_VALUE not in prediction.columns


def test_race_day_prediction_without_pool_odds_uses_the_pool_free_models(season_db: Path, trained: tuple[Path, str],
                                                                         figure_cache: Path):
    models, _ = trained
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models, figure_cache).run(
            season.CARD_RACE_ID, PredictionTiming.RACE_DAY, OddsInput.of(CARD_ODDS_TEXTS))
        data = race_day_dataset_builder(con, figure_cache).build_prediction_data(
            season.CARD_RACE_ID, PredictionTiming.RACE_DAY, odds=CARD_ODDS)
    # 合成DB には券種のオッズが無いので、券種の支持を外して、券種の支持を使わないモデルで予測する
    assert PoolAvailability().missing(data)
    expected = SegmentedPrediction(ModelSegments(), models / POOL_FREE_FOLDER).predict(PoolFreeData().prediction(data))
    np.testing.assert_allclose(prediction[PROBABILITY].to_numpy(), expected[AVERAGE].to_numpy())


def test_race_day_prediction_shows_the_market_top3_rate_and_the_place_value(season_db: Path, trained, figure_cache: Path):
    models, _ = trained
    estimator = PlacePriceEstimator().fit(pd.Series([2.0, 3.0]), pd.Series([240.0, 330.0]))
    with db.open_db(season_db) as con:
        prediction = _workflow(con, models, figure_cache, estimator).run(
            season.CARD_RACE_ID, PredictionTiming.RACE_DAY, OddsInput.of(CARD_ODDS_TEXTS))
    # オッズから見た3着以内率はレースで合計 3。合成DB の 1R には締め切り前の複勝オッズがあるので、出走する全頭に期待値が出る
    assert prediction[TOP3_RATE].sum() == pytest.approx(3.0)
    assert {PLACE_PROBABILITY, PLACE_VALUE} <= set(prediction.columns) and prediction[PLACE_VALUE].notna().all()


def _run_command(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as stopped:
        CommandLine().run(argv)
    return stopped.value.code


def test_command_predicts_a_race_by_date_venue_and_number(season_db: Path, trained, figure_cache: Path, capsys,
                                                          monkeypatch: pytest.MonkeyPatch):
    models, _ = trained
    # 展開のモデルは合成DB では学べないので、展開の予測は予測の無い表にする（P は欠損値）
    monkeypatch.setattr(predict_command.DevelopmentPaceWorkflow, "run", lambda self, con, race_id, timing, given: pd.DataFrame())
    code = _run_command([
        "predict", "--date", "2025-01-11", "--venue", "東京", "--race", "2", "--timing", "木曜",
        "--figure-cache", str(figure_cache), "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 8
    assert lines[0] == f"順位,馬番,馬名,{PROBABILITY},LightGBM,CatBoost"


def test_command_shows_the_odds_it_used_on_race_day(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--odds", *CARD_ODDS_TEXTS,
        "--db", str(season_db), "--models", str(models), "--format", "csv",
    ])
    lines = capsys.readouterr().out.strip().splitlines()
    assert code == 0 and len(lines) == 1 + 7
    # 学習のときに複勝の見込みの倍率を保存してあるので、複勝的中の確率と複勝の期待値の列も出る
    assert lines[0] == (f"順位,馬番,馬名,{WIN_ODDS},{TOP3_RATE},{PLACE_PROBABILITY},{PLACE_VALUE},{PROBABILITY},"
                        "LightGBM,CatBoost")


def test_command_asks_for_odds_when_the_database_has_none(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.CARD_RACE_ID, "--timing", "当日", "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "--odds" in capsys.readouterr().err


def test_command_saves_the_place_price_with_the_models(trained: tuple[Path, str]):
    models, _ = trained
    # 複勝の見込みの倍率も、モデルと一緒に保存する
    assert (models / PLACE_PRICE_FILE).exists()


def test_command_rejects_periods_out_of_order(season_db: Path, capsys):
    code = _run_command([
        "train", "--train-from", "2024-07-01", "--valid-from", "2024-01-01", "--db", str(season_db),
    ])
    assert code == 1 and "学習データの始まり" in capsys.readouterr().err


def test_command_reports_errors_in_one_line(season_db: Path, trained, capsys):
    models, _ = trained
    code = _run_command([
        "predict", season.JUMP_CARD_RACE_ID, "--timing", "当日",
        "--db", str(season_db), "--models", str(models),
    ])
    assert code == 1 and "障害レース" in capsys.readouterr().err
    assert _run_command(["predict", "--timing", "当日", "--db", str(season_db)]) == 1
