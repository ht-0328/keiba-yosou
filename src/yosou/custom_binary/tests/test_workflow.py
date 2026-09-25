from dataclasses import replace
import json

import numpy as np
import pandas as pd
import pytest
import yaml

from 共通 import db
from yosou.shared.dataset.column_names import POPULARITY, RACE_ID, RACE_DATE
from yosou.shared.dataset import RaceRecordsLoader
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.feature_kind import FeatureKind
from yosou.shared.tests import synthetic_season as season

from ..command import CommandLine
from ..dataset import CustomDataset, popularity_mask, targets
from ..evaluation import evaluate, scores
from ..feature.registrations import default_registry
from ..feature.registry import FeatureRegistry
from ..model_store import ModelStore
from ..settings import ModelSettings, PopularityRange
from .. import workflow


FEATURES = ("競馬場", "芝ダ", "距離", "馬齢", "斤量", "前走の着順", "前走からの日数", "近5走の平均着順", "推定脚質", "騎手")
POPS = [f"{horse}:{rank}" for rank, horse in enumerate([3, 5, 1, 2, 4, 6, 7], 1)]


@pytest.fixture
def settings(tmp_path, season_period):
    config = {
        "name": "synthetic", "features_file": "features.txt", "target": "馬券内", "timing": "当日",
        "popularity": {"min": 2, "max": 6},
        "training": {
            "warmup_from": season_period.warmup_first_day.isoformat(),
            "train_from": season_period.train_first_day.isoformat(),
            "valid_from": season_period.valid_first_day.isoformat(),
            "test_from": season_period.test_first_day.isoformat(),
        },
        "lightgbm": {"early_stopping_rounds": 3, "min_category_count": 2, "params": {"n_estimators": 8, "min_child_samples": 5}},
        "catboost": {"early_stopping_rounds": 3, "params": {"iterations": 8, "depth": 3}},
    }
    (tmp_path / "model.yml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    (tmp_path / "features.txt").write_text("\n".join(FEATURES), encoding="utf-8")
    return ModelSettings.load(tmp_path / "model.yml", default_registry())


@pytest.mark.parametrize("target,timing", [("馬券内", PredictionTiming.RACE_DAY), ("馬券外", PredictionTiming.DAY_BEFORE), ("勝利", PredictionTiming.THURSDAY)])
def test_real_models_roundtrip_ten_columns_and_evaluation(season_db, settings, tmp_path, target, timing):
    settings = replace(settings, target=target, timing=timing)
    registry = default_registry()
    with db.open_db(season_db) as con:
        data = CustomDataset(con, settings, registry).training()
    assert tuple(data.features.columns) == FEATURES
    assert data.baseline is None
    assert data.evaluation[POPULARITY].between(2, 6).all()
    assert data.ids[RACE_DATE].max() < pd.Timestamp("2025-01-01")  # 未確定の出馬表は学習しない
    store = ModelStore(tmp_path / "models")
    workflow.fit_and_save(data, settings, registry, store)
    (tmp_path / "features.txt").unlink()
    (tmp_path / "model.yml").unlink()
    loaded, ensemble = store.load(registry)
    assert loaded.as_dict() == settings.as_dict()
    test = data.between(settings.period.test_first_day, None)
    assert len(evaluate(ensemble, test)) > 3
    assert np.isfinite(ensemble.predict_proba(test)).all()
    if timing is PredictionTiming.THURSDAY:
        race_id = season.ENTRY_LIST_RACE_ID
        with db.open_db(season_db) as con:
            names = RaceRecordsLoader(con).load(race_id).entries["horse_name"].tolist()
        pops = [f"{name}:{rank}" for rank, name in enumerate(names, 1)]
    else:
        race_id, pops = season.CARD_RACE_ID, POPS
    result = workflow.predict(race_id, store.root, season_db, registry, pops)
    assert len(result) == 5
    column = result.columns.index(f"{target}の確率")
    probabilities = [row[column] for row in result.rows]
    assert probabilities == sorted(probabilities, reverse=True)
    assert all(0 <= probability <= 1 for probability in probabilities)
    workflow.test_evaluation(store.root, season_db, registry)
    assert (store.root / "test_evaluation.json").exists()
    manifest = json.loads((store.root / "model.json").read_text(encoding="utf-8"))
    assert len(manifest["settings"]["features"]) == 10
    assert manifest["code_version"]["python_source_sha256"]
    with pytest.raises(ValueError, match="既に存在"):
        workflow.fit_and_save(data, settings, registry, store)


def test_custom_feature_registration_is_sufficient_for_train_and_predict(season_db, settings, tmp_path):
    class PreviousFinishSquare:
        name = "前走着順の二乗"
        description = "新項目の追加例"
        kind = FeatureKind.NUMERIC
        known_from = PredictionTiming.THURSDAY
        dependencies = ("前走の着順",)

        def compute(self, records, dependencies):
            return dependencies["前走の着順"] ** 2

    registry = FeatureRegistry([*default_registry().definitions.values(), PreviousFinishSquare()])
    settings = replace(settings, selected=("馬齢", "前走着順の二乗"))
    with db.open_db(season_db) as con:
        data = CustomDataset(con, settings, registry).training()
    assert list(data.features.columns) == ["馬齢", "前走着順の二乗"]
    store = ModelStore(tmp_path / "extension")
    workflow.fit_and_save(data, settings, registry, store)
    assert len(workflow.predict(season.CARD_RACE_ID, store.root, season_db, registry, POPS)) == 5
    changed = PreviousFinishSquare()
    changed.kind = FeatureKind.CATEGORICAL
    changed_registry = FeatureRegistry([*default_registry().definitions.values(), changed])
    with pytest.raises(ValueError, match="現在の実装と違います"):
        store.load(changed_registry)


def test_comparison_features_use_entire_field_and_training_dates(season_db, settings):
    registry = default_registry()
    selected = ("斤量とレースの平均との差",)
    all_settings = replace(settings, selected=selected, popularity=PopularityRange())
    with db.open_db(season_db) as con:
        full = CustomDataset(con, all_settings, registry).training()
        part = CustomDataset(con, replace(all_settings, popularity=PopularityRange(2, 6)), registry).training()
    pd.testing.assert_frame_equal(part.features, full.features.loc[part.features.index])
    sums = full.features[selected[0]].groupby(full.ids[RACE_ID]).sum()
    assert np.allclose(sums, 0, atol=1e-8)
    assert "斤量" not in part.features


def test_all_builtin_features_match_existing_builder(season_db, settings):
    from yosou.shared.dataset import HistoryRecordsLoader
    from yosou.shared.feature import FeatureBuilder
    from yosou.longshots_in_top3.dataset.dataset_assembly import _FEATURE_GROUPS
    from ..feature.builder import SelectedFeatureBuilder
    from ..feature.builtin import builtin_features

    registry = default_registry()
    # 旧方式にある特徴量（既存のまとまり）だけを比べる。追加した特徴量（券種オッズなど）は旧方式に無い。
    selected = tuple(feature.name for feature in builtin_features())
    with db.open_db(season_db) as con:
        records = HistoryRecordsLoader(con).load(settings.period.warmup_first_day)
    # 1レースの全頭で旧方式と一致することを確認する。
    last_race = records.entries["race_id"].iloc[-1]
    records = records.with_entries(records.entries[records.entries["race_id"] == last_race])
    expected = FeatureBuilder(registry.catalog(selected), _FEATURE_GROUPS).build(records, settings.timing)
    actual = SelectedFeatureBuilder(registry, selected, settings.timing).build(records)
    pd.testing.assert_frame_equal(actual, expected)


@pytest.mark.parametrize("bounds,expected", [(PopularityRange(), [0, 1, 2, 3]), (PopularityRange(2, 3), [1, 2]), (PopularityRange(3), [2, 3]), (PopularityRange(maximum=2), [0, 1]), (PopularityRange(8), [])])
def test_popularity_boundaries(bounds, expected):
    rows = pd.DataFrame({"popularity": [1, 2, 3, 4]})
    assert rows[popularity_mask(rows, bounds)].index.tolist() == expected


def test_missing_popularity_rejected_only_when_needed():
    rows = pd.DataFrame({"popularity": [1, None]})
    assert popularity_mask(rows, PopularityRange()).all()
    with pytest.raises(ValueError, match="人気が不明"):
        popularity_mask(rows, PopularityRange(1, 3))


def test_labels_for_ties_dnf_and_disqualification():
    rows = pd.DataFrame({"finish": [1, 1, 2, 3, 3, 4, None, None]})
    assert targets(rows, "馬券内")["馬券内"].tolist() == [1, 1, 1, 1, 1, 0, 0, 0]
    assert targets(rows, "馬券外")["馬券外"].tolist() == [0, 0, 0, 0, 0, 1, 1, 1]
    assert targets(rows, "勝利")["勝利"].tolist() == [1, 1, 0, 0, 0, 0, 0, 0]


def test_empty_and_one_class_scores():
    assert scores(pd.Series([], dtype=int), np.array([]))["件数"] == 0
    result = scores(pd.Series([0, 0]), np.array([0.2, 0.3]))
    assert result["AUC"] is None and "1クラス" in result["注記"]


def test_missing_announcements_and_no_candidates(season_db, settings):
    with db.open_db(season_db) as con:
        dataset = CustomDataset(con, replace(settings, popularity=PopularityRange(20)), default_registry())
        assert len(dataset.prediction(season.CARD_RACE_ID, {int(pair.split(":")[0]): int(pair.split(":")[1]) for pair in POPS})) == 0
        weighted = CustomDataset(con, replace(settings, selected=("馬体重",), popularity=PopularityRange()), default_registry())
        with pytest.raises(ValueError, match="未取得"):
            weighted.prediction(season.ENTRY_LIST_RACE_ID)
        with pytest.raises(ValueError, match="障害"):
            dataset.prediction(season.JUMP_CARD_RACE_ID)


def test_empty_and_one_class_training_fail_before_save(season_db, settings, tmp_path):
    registry = default_registry()
    with db.open_db(season_db) as con:
        data = CustomDataset(con, settings, registry).training()
    store = ModelStore(tmp_path / "not_saved")
    empty = data.where(pd.Series(False, index=data.ids.index))
    with pytest.raises(ValueError, match="空"):
        workflow.fit_and_save(empty, settings, registry, store)
    with pytest.raises(ValueError, match="1クラス"):
        workflow.fit_and_save(data.where(data.label.eq(0)), settings, registry, store)
    assert not store.root.exists()


def test_cli_train_predict_evaluate_json(season_db, settings, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    models = tmp_path / "reports" / "custom_binary" / settings.name
    for args in [
        ["train", "--config", str(tmp_path / "model.yml")],
        ["predict", season.CARD_RACE_ID, "--models", str(models), "--pops", *POPS],
        ["evaluate", "--models", str(models)],
    ]:
        with pytest.raises(SystemExit) as stopped:
            CommandLine().run([*args, "--db", str(season_db), "--format", "json"])
        assert stopped.value.code == 0
        assert json.loads(capsys.readouterr().out)
