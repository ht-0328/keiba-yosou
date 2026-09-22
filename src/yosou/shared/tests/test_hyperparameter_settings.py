"""設定ファイルの読み方（設計書 14）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from ..setting import HyperparameterSettings


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "settings.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_are_the_design_initial_values():
    settings = HyperparameterSettings.load()
    assert dict(settings.lightgbm.params) == {
        "learning_rate": 0.05, "n_estimators": 2000, "num_leaves": 31, "min_child_samples": 100,
        "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "random_state": 42,
    }
    assert settings.lightgbm.early_stopping_rounds == 100 and settings.lightgbm.min_category_count == 2000
    assert dict(settings.catboost.params) == {
        "learning_rate": 0.05, "iterations": 2000, "depth": 6, "l2_leaf_reg": 3, "random_seed": 42,
    }
    assert settings.catboost.early_stopping_rounds == 100


def test_file_overrides_only_what_it_writes(tmp_path: Path):
    path = _write(tmp_path, "[lightgbm.params]\nnum_leaves = 63\n\n[catboost]\nearly_stopping_rounds = 50\n")
    settings = HyperparameterSettings.load(path)
    assert settings.lightgbm.params["num_leaves"] == 63
    assert settings.lightgbm.params["learning_rate"] == 0.05
    assert settings.catboost.early_stopping_rounds == 50 and settings.catboost.params["depth"] == 6


@pytest.mark.parametrize(("text", "message"), [
    ("[lightgbm.params]\nnum_leaf = 63\n", "知らない設定の名前"),
    ("[xgboost]\nmax_depth = 3\n", "知らない設定の名前"),
    ("[lightgbm.params]\nobjective = 'regression'\n", "目的関数"),
    ("[catboost.params]\nloss_function = 'RMSE'\n", "目的関数"),
    ("lightgbm = 1\n", "表"),
    ("[lightgbm\n", "読めません"),
])
def test_wrong_names_stop_with_error(tmp_path: Path, text: str, message: str):
    with pytest.raises(ValueError, match=message):
        HyperparameterSettings.load(_write(tmp_path, text))


def test_missing_file_is_reported(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        HyperparameterSettings.load(tmp_path / "none.toml")


def test_to_dict_round_trips():
    settings = HyperparameterSettings.load()
    assert HyperparameterSettings.from_dict(settings.to_dict()).to_dict() == settings.to_dict()
