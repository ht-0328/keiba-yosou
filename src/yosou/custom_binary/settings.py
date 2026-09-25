"""YAMLを厳密に読み、学習・予想に共通の設定値にする。"""

from dataclasses import dataclass
from datetime import date
import math
from pathlib import Path
import re

import yaml

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH
from yosou.shared.dataset import TrainingPeriod
from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings
from yosou.shared.setting.settings_name_check import SettingsNameCheck
from yosou.shared.setting.settings_overlay import SettingsOverlay

from .feature.registry import FeatureRegistry
from .row_conditions import RowConditions


class UniqueKeyLoader(yaml.SafeLoader):
    """安全なYAML読込に、キー重複と文字列以外のキーの拒否を加える。"""

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError(f"YAMLのキーは文字列にしてください（{key_node.start_mark.line + 1}行）")
            if key in result:
                raise ValueError(f"YAMLのキーが重複しています: {key}（{key_node.start_mark.line + 1}行）")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def mapping(value, allowed: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{where}はキーと値の組で指定してください")
    unknown = value.keys() - allowed
    if unknown:
        raise ValueError(f"{where}に未知のキーがあります: {', '.join(sorted(unknown))}")
    return value


@dataclass(frozen=True)
class PopularityRange:
    minimum: int | None = None
    maximum: int | None = None

    def __post_init__(self) -> None:
        for value in (self.minimum, self.maximum):
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError("人気範囲は1以上の整数で指定してください")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("人気範囲のminはmax以下にしてください")

    @property
    def bounded(self) -> bool:
        return self.minimum is not None or self.maximum is not None

    def as_dict(self) -> dict:
        return {key: value for key, value in (("min", self.minimum), ("max", self.maximum)) if value is not None}


def period_from(values: dict) -> TrainingPeriod:
    defaults = TrainingPeriod.default()
    allowed = {"warmup_from", "train_from", "valid_from", "test_from"}
    mapping(values, allowed, "training")

    def day(name: str, fallback: date | None) -> date | None:
        value = values.get(name, fallback)
        if value is None and name not in values:
            return None
        if type(value) is date:
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        raise ValueError(f"training.{name}はYYYY-MM-DDで指定してください")

    return TrainingPeriod.starting(
        day("train_from", defaults.train_first_day), day("valid_from", defaults.valid_first_day),
        day("test_from", defaults.test_first_day), day("warmup_from", None),
    )


def hyperparameters(values: dict) -> HyperparameterSettings:
    defaults = HyperparameterSettings.load(None, DEFAULT_SETTINGS_PATH).to_dict()
    SettingsNameCheck(defaults).check(values, "YAML")

    def check_types(overrides: dict, expected: dict, path: str = "") -> None:
        for key, value in overrides.items():
            name = f"{path}.{key}" if path else key
            default = expected[key]
            if isinstance(default, dict):
                check_types(value, default, name)
            elif isinstance(default, float):
                if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                    raise ValueError(f"{name}は正の有限な数値にしてください")
            elif type(value) is not type(default):
                raise ValueError(f"{name}の型が違います（{type(default).__name__}で指定）")
            elif isinstance(value, int):
                can_be_zero = key in {"random_state", "random_seed", "subsample_freq"}
                if value < (0 if can_be_zero else 1):
                    raise ValueError(f"{name}の値が小さすぎます")
            if key in {"subsample", "colsample_bytree"} and value > 1:
                raise ValueError(f"{name}は1以下にしてください")

    check_types(values, defaults)
    return HyperparameterSettings.from_dict(SettingsOverlay(defaults).apply(values))


@dataclass(frozen=True)
class ModelSettings:
    name: str
    selected: tuple[str, ...]
    target: str
    timing: PredictionTiming
    popularity: PopularityRange
    period: TrainingPeriod
    parameters: HyperparameterSettings
    conditions: RowConditions = RowConditions()
    odds_baseline: bool = False

    @classmethod
    def load(cls, path: Path, registry: FeatureRegistry) -> "ModelSettings":
        try:
            values = yaml.load(path.read_text(encoding="utf-8-sig"), Loader=UniqueKeyLoader)
        except yaml.YAMLError as error:
            raise ValueError(f"YAMLを読み込めません: {path}: {error}") from error
        allowed = {
            "name", "features_file", "target", "timing", "popularity", "conditions", "odds_baseline", "training",
            "lightgbm", "catboost",
        }
        mapping(values, allowed, str(path))
        required = {"name", "features_file", "target", "timing"}
        for key in required:
            if not isinstance(values.get(key), str) or not values[key].strip():
                raise ValueError(f"{key}は空でない文字列で指定してください")
        _check_identity(values["name"], values["target"], values["timing"])
        timing = PredictionTiming.parse(values["timing"])
        selected = registry.read_selection(path.parent / values["features_file"], timing)
        return cls.from_values(values, selected, registry)

    @classmethod
    def from_values(cls, values: dict, selected: tuple[str, ...], registry: FeatureRegistry) -> "ModelSettings":
        """YAMLを読んだ後の値から作る。探索のように設定をプログラムで組み立てるときもここを通す。"""
        _check_identity(values["name"], values["target"], values["timing"])
        popularity = mapping(values.get("popularity", {}), {"min", "max"}, "popularity")
        for key, value in popularity.items():
            if value is None:
                raise ValueError(f"popularity.{key}は省略するか正の整数にしてください")
        return cls(
            values["name"], selected, values["target"], PredictionTiming.parse(values["timing"]),
            PopularityRange(popularity.get("min"), popularity.get("max")),
            period_from(values.get("training", {})),
            hyperparameters({key: values[key] for key in ("lightgbm", "catboost") if key in values}),
            RowConditions.parse(values.get("conditions", {}), registry, PredictionTiming.parse(values["timing"])),
            _odds_baseline(values.get("odds_baseline", False), values["timing"]),
        )

    @classmethod
    def from_saved(cls, values: dict, registry: FeatureRegistry) -> "ModelSettings":
        selected = values.get("features")
        if not isinstance(selected, list) or not selected or any(not isinstance(name, str) for name in selected):
            raise ValueError("保存された特徴量一覧が不正です")
        if len(set(selected)) != len(selected):
            raise ValueError("保存された特徴量一覧に重複があります")
        result = cls.from_values(values, tuple(selected), registry)
        registry.order(result.selected, result.timing)
        return result

    def as_dict(self) -> dict:
        return {
            "name": self.name, "features": list(self.selected), "target": self.target,
            "timing": self.timing.label, "popularity": self.popularity.as_dict(),
            "conditions": self.conditions.as_dict(), "odds_baseline": self.odds_baseline,
            "training": {
                "warmup_from": self.period.warmup_first_day.isoformat(),
                "train_from": self.period.train_first_day.isoformat(),
                "valid_from": self.period.valid_first_day.isoformat(),
                "test_from": self.period.test_first_day.isoformat(),
            }, **self.parameters.to_dict(),
        }


def _odds_baseline(value, timing: str) -> bool:
    if type(value) is not bool:
        raise ValueError("odds_baselineはtrueかfalseで指定してください")
    if value and timing == "木曜":
        raise ValueError("odds_baselineはオッズが分かる前日・当日だけで使えます")
    return value


def _check_identity(name: str, target: str, timing: str) -> None:
    if not isinstance(name, str) or not re.fullmatch(r"[\w-]+", name):
        raise ValueError("nameは文字・数字・アンダースコア・ハイフンで指定してください")
    if name.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        raise ValueError("nameにWindowsの予約名は使えません")
    if target not in ("馬券内", "馬券外", "勝利"):
        raise ValueError("targetは馬券内・馬券外・勝利から指定してください")
    if timing not in ("木曜", "前日", "当日"):
        raise ValueError("timingは木曜・前日・当日から指定してください")
