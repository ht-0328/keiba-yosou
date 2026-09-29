"""YAML の lightgbm・catboost: 初期値の設定ファイルに、YAML に書いた項目だけを上書きする。"""

import math
from pathlib import Path

from yosou.shared.setting import HyperparameterSettings
from yosou.shared.setting.settings_name_check import SettingsNameCheck
from yosou.shared.setting.settings_overlay import SettingsOverlay

from .default_settings_path import DEFAULT_SETTINGS_PATH

#: 0 を書いてよい整数の項目（乱数の種と、間引きの頻度）。
CAN_BE_ZERO = {"random_state", "random_seed", "subsample_freq"}
#: 1 以下にする割合の項目。
AT_MOST_ONE = {"subsample", "colsample_bytree"}


class HyperparameterReader:
    """名前は初期値にあるものだけ、型は初期値と同じもの、値は正の数（一部は 0 も可）だけを受け付ける。"""

    def __init__(self, defaults_path: Path = DEFAULT_SETTINGS_PATH) -> None:
        self._defaults_path = defaults_path

    def read(self, values: dict) -> HyperparameterSettings:
        defaults = HyperparameterSettings.load(None, self._defaults_path).to_dict()
        SettingsNameCheck(defaults).check(values, "YAML")
        self._check_types(values, defaults, "")
        return HyperparameterSettings.from_dict(SettingsOverlay(defaults).apply(values))

    def _check_types(self, overrides: dict, expected: dict, path: str) -> None:
        for key, value in overrides.items():
            name = f"{path}.{key}" if path else key
            self._check_value(key, value, expected[key], name)

    def _check_value(self, key: str, value, default, name: str) -> None:
        if isinstance(default, dict):
            self._check_types(value, default, name)
        elif isinstance(default, float):
            self._check_positive_number(value, name)
        elif type(value) is not type(default):
            raise ValueError(f"{name}の型が違います（{type(default).__name__}で指定）")
        elif isinstance(value, int):
            self._check_integer(key, value, name)
        if key in AT_MOST_ONE and value > 1:
            raise ValueError(f"{name}は1以下にしてください")

    def _check_positive_number(self, value, name: str) -> None:
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name}は正の有限な数値にしてください")

    def _check_integer(self, key: str, value: int, name: str) -> None:
        if value < (0 if key in CAN_BE_ZERO else 1):
            raise ValueError(f"{name}の値が小さすぎます")
