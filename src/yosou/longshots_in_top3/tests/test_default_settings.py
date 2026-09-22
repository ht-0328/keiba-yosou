"""この予想のハイパーパラメータの初期値が、設計書 12・13 の値どおりであることを固定する。

設定ファイルの読み方そのもの（重ね方・名前の誤り）は ``yosou/shared/tests/test_hyperparameter_settings.py``。
"""

from __future__ import annotations

from yosou.shared.setting import HyperparameterSettings

from ..setting import DEFAULT_SETTINGS_PATH


def test_defaults_are_the_design_initial_values():
    settings = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
    assert dict(settings.lightgbm.params) == {
        "learning_rate": 0.05, "n_estimators": 2000, "num_leaves": 31, "min_child_samples": 100,
        "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "random_state": 42,
    }
    assert settings.lightgbm.early_stopping_rounds == 100 and settings.lightgbm.min_category_count == 2000
    assert dict(settings.catboost.params) == {
        "learning_rate": 0.05, "iterations": 2000, "depth": 6, "l2_leaf_reg": 3, "random_seed": 42,
    }
    assert settings.catboost.early_stopping_rounds == 100
