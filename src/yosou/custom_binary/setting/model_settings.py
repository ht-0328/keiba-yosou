"""YAMLを厳密に読み、学習・予想に共通の設定値にする。"""

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from yosou.shared.dataset import TrainingPeriod
from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings

from ..feature.registry import FeatureRegistry
from .hyperparameter_reader import HyperparameterReader
from .popularity_range import PopularityRange
from .row_conditions import RowConditions
from .training_period_reader import TrainingPeriodReader
from .unique_key_loader import UniqueKeyLoader
from .yaml_mapping import YamlMapping

#: 設定の YAML に書ける項目。
ALLOWED = {
    "name", "features_file", "target", "timing", "popularity", "conditions", "odds_baseline", "training",
    "lightgbm", "catboost",
}
#: 省略できない項目（空でない文字列）。
REQUIRED = {"name", "features_file", "target", "timing"}
#: Windows でフォルダの名前に使えない予約名。
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


@dataclass(frozen=True)
class ModelSettings:
    """1つのモデルの設定（名前・選んだ特徴量・目的・時点・人気範囲・期間・ハイパーパラメータ・条件・オッズの基準）。"""

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
        YamlMapping().check(values, ALLOWED, str(path))
        for key in REQUIRED:
            if not isinstance(values.get(key), str) or not values[key].strip():
                raise ValueError(f"{key}は空でない文字列で指定してください")
        cls._check_identity(values["name"], values["target"], values["timing"])
        timing = PredictionTiming.parse(values["timing"])
        selected = registry.read_selection(path.parent / values["features_file"], timing)
        return cls.from_values(values, selected, registry)

    @classmethod
    def from_values(cls, values: dict, selected: tuple[str, ...], registry: FeatureRegistry) -> "ModelSettings":
        """YAMLを読んだ後の値から作る。探索のように設定をプログラムで組み立てるときもここを通す。"""
        cls._check_identity(values["name"], values["target"], values["timing"])
        popularity = YamlMapping().check(values.get("popularity", {}), {"min", "max"}, "popularity")
        for key, value in popularity.items():
            if value is None:
                raise ValueError(f"popularity.{key}は省略するか正の整数にしてください")
        return cls(
            values["name"], selected, values["target"], PredictionTiming.parse(values["timing"]),
            PopularityRange(popularity.get("min"), popularity.get("max")),
            TrainingPeriodReader().read(values.get("training", {})),
            HyperparameterReader().read({key: values[key] for key in ("lightgbm", "catboost") if key in values}),
            RowConditions.parse(values.get("conditions", {}), registry, PredictionTiming.parse(values["timing"])),
            cls._odds_baseline(values.get("odds_baseline", False), values["timing"]),
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

    @staticmethod
    def _odds_baseline(value, timing: str) -> bool:
        if type(value) is not bool:
            raise ValueError("odds_baselineはtrueかfalseで指定してください")
        if value and timing == "木曜":
            raise ValueError("odds_baselineはオッズが分かる前日・当日だけで使えます")
        return value

    @staticmethod
    def _check_identity(name: str, target: str, timing: str) -> None:
        if not isinstance(name, str) or not re.fullmatch(r"[\w-]+", name):
            raise ValueError("nameは文字・数字・アンダースコア・ハイフンで指定してください")
        if name.upper() in RESERVED_NAMES:
            raise ValueError("nameにWindowsの予約名は使えません")
        if target not in ("馬券内", "馬券外", "勝利"):
            raise ValueError("targetは馬券内・馬券外・勝利から指定してください")
        if timing not in ("木曜", "前日", "当日"):
            raise ValueError("timingは木曜・前日・当日から指定してください")
