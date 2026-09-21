"""2つのモデルのハイパーパラメータの設定。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .catboost_settings import CatBoostSettings
from .lightgbm_settings import LightGbmSettings
from .settings_file import SettingsFile
from .settings_name_check import SettingsNameCheck
from .settings_overlay import SettingsOverlay

#: 初期値の設定ファイル。
DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "default_settings.toml"
#: モデルの引数を書く表の名前（``[lightgbm.params]`` の ``params``）。
_PARAMS = "params"


@dataclass(frozen=True)
class HyperparameterSettings:
    """2つのモデルの設定。3つの時点のモデルは、同じ設定で学習する（設計書 14）。"""

    lightgbm: LightGbmSettings
    catboost: CatBoostSettings

    @classmethod
    def load(cls, path: Path | None = None) -> HyperparameterSettings:
        """設定ファイルを読む。``path`` が None なら初期値のまま。名前の誤りは ``ValueError``。"""
        defaults = SettingsFile(DEFAULT_SETTINGS_PATH).read()
        if path is None:
            return cls.from_dict(defaults)
        overrides = SettingsFile(path).read()
        SettingsNameCheck(defaults).check(overrides, str(path))
        return cls.from_dict(SettingsOverlay(defaults).apply(overrides))

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> HyperparameterSettings:
        """``to_dict`` の形の辞書から作る。モデルと一緒に保存した設定を読み直すときにも使う。"""
        lightgbm, catboost = values["lightgbm"], values["catboost"]
        return cls(
            lightgbm=LightGbmSettings(
                params=MappingProxyType(dict(lightgbm[_PARAMS])),
                early_stopping_rounds=int(lightgbm["early_stopping_rounds"]),
                min_category_count=int(lightgbm["min_category_count"]),
            ),
            catboost=CatBoostSettings(
                params=MappingProxyType(dict(catboost[_PARAMS])),
                early_stopping_rounds=int(catboost["early_stopping_rounds"]),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """設定ファイルと同じ形の辞書。学習したモデルと一緒に保存する。"""
        return {
            "lightgbm": {
                "early_stopping_rounds": self.lightgbm.early_stopping_rounds,
                "min_category_count": self.lightgbm.min_category_count,
                _PARAMS: dict(self.lightgbm.params),
            },
            "catboost": {
                "early_stopping_rounds": self.catboost.early_stopping_rounds,
                _PARAMS: dict(self.catboost.params),
            },
        }
