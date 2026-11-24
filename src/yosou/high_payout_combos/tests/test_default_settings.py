"""この予想のハイパーパラメータの初期値が、回収率を確かめたときの値どおりであることを固定する。

設定ファイルの読み方そのもの（重ね方・名前の誤り）は ``yosou/shared/tests/test_hyperparameter_settings.py``。
"""

from __future__ import annotations

from yosou.shared.setting import HyperparameterSettings

from ..setting import DEFAULT_SETTINGS_PATH


def test_初期値は_回収率を確かめたときの値() -> None:
    settings = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
    assert dict(settings.lightgbm.params) == {
        "learning_rate": 0.03, "n_estimators": 3000, "num_leaves": 31, "min_child_samples": 300, "colsample_bytree": 0.5,
        "subsample": 0.7, "subsample_freq": 1, "reg_lambda": 20, "max_bin": 127, "random_state": 0, "n_jobs": 3,
    }
    assert settings.lightgbm.early_stopping_rounds == 100
    assert dict(settings.catboost.params) == {
        "learning_rate": 0.05, "iterations": 3000, "depth": 6, "l2_leaf_reg": 10, "rsm": 0.5, "border_count": 128,
        "bootstrap_type": "Bernoulli", "subsample": 0.7, "random_seed": 0, "thread_count": 3,
    }
    assert settings.catboost.early_stopping_rounds == 100
