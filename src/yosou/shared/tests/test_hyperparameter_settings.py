"""設定ファイルの読み方（設計書 14）。

初期値のファイルは予想ごとに持つので、ここではテスト用の初期値（``conftest.py`` の ``DEFAULT_SETTINGS``）を
渡して、読み方だけを確かめる。手本の予想の初期値が設計書どおりかは
``yosou/form_aptitude_top3/tests/test_default_settings.py``。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ..setting import HyperparameterSettings


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "settings.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_no_file_keeps_the_initial_values(default_settings_path: Path):
    settings = HyperparameterSettings.load(None, defaults=default_settings_path)
    assert settings.lightgbm.params["learning_rate"] == 0.05
    assert settings.lightgbm.early_stopping_rounds == 100 and settings.lightgbm.min_category_count == 2000
    assert settings.catboost.params["depth"] == 6 and settings.catboost.early_stopping_rounds == 100


def test_file_overrides_only_what_it_writes(tmp_path: Path, default_settings_path: Path):
    path = _write(tmp_path, "[lightgbm.params]\nnum_leaves = 63\n\n[catboost]\nearly_stopping_rounds = 50\n")
    settings = HyperparameterSettings.load(path, defaults=default_settings_path)
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
def test_wrong_names_stop_with_error(tmp_path: Path, default_settings_path: Path,
                                     text: str, message: str):
    with pytest.raises(ValueError, match=message):
        HyperparameterSettings.load(_write(tmp_path, text), defaults=default_settings_path)


def test_missing_file_is_reported(tmp_path: Path, default_settings_path: Path):
    with pytest.raises(FileNotFoundError):
        HyperparameterSettings.load(tmp_path / "none.toml", defaults=default_settings_path)


def test_to_dict_round_trips(default_settings_path: Path):
    settings = HyperparameterSettings.load(None, defaults=default_settings_path)
    assert HyperparameterSettings.from_dict(settings.to_dict()).to_dict() == settings.to_dict()
