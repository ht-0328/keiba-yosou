"""この予想の方針（設定ファイルの中身）。"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from yosou.shared.feature import PredictionTiming
from yosou.shared.setting.settings_file import SettingsFile
from yosou.shared.setting.settings_name_check import SettingsNameCheck
from yosou.shared.setting.settings_overlay import SettingsOverlay

from .option_names import (
    CATEGORICAL_ENCODINGS, COLUMN_WEIGHTINGS, ENCODING_ONE_HOT, SCALING_STANDARD, SCALINGS, SPLIT_BY_COURSE,
    UNIT_SPLITS, WEIGHTING_NONE,
)

#: この予想の初期値の設定ファイル。
DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "default_settings.toml"
#: 予測に使える時点。木曜は人気が分からないので使えない。
_TIMINGS = (PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY)
#: あとから足した項目の、足す前に保存した一式を読むときの値（足す前の作り方と同じになる値）。
_ADDED_LATER: dict[str, Any] = {
    "unit_split": SPLIT_BY_COURSE, "scaling": SCALING_STANDARD, "categorical_encoding": ENCODING_ONE_HOT,
    "column_weighting": WEIGHTING_NONE, "column_weighting_keep": 0,
}


@dataclass(frozen=True)
class BuyOrFadeSettings:
    """方針の値（設計書 14）。項目の意味は ``default_settings.toml`` のコメントにある。

    ``load()`` で、初期値のファイルに利用者のファイルを重ねて作る。学習したモデルと一緒に保存し、
    予測のときに同じ方針を使う（``to_dict``・``from_dict``）。
    """

    min_unit_rows: int
    unit_split: str
    timing: PredictionTiming
    excluded_features: tuple[str, ...]
    add_missing_flags: bool
    scaling: str
    categorical_encoding: str
    group_weights: Mapping[str, float]
    column_weighting: str
    column_weighting_keep: int
    k: int
    fade_margin: float
    win_margin: float
    win_and_place_win_stake: int
    win_and_place_place_stake: int
    place_only_place_stake: int
    train_first_year: int
    first_year: int
    last_year: int
    tune_last_year: int

    def __post_init__(self) -> None:
        if self.timing not in _TIMINGS:
            raise ValueError(f"features.timing は 前日 か 当日 にしてください（{self.timing.label}では人気が分かりません）")
        _check_choice("unit.split", self.unit_split, UNIT_SPLITS)
        _check_choice("features.scaling", self.scaling, SCALINGS)
        _check_choice("features.categorical", self.categorical_encoding, CATEGORICAL_ENCODINGS)
        _check_choice("features.column_weighting.method", self.column_weighting, COLUMN_WEIGHTINGS)
        if self.column_weighting_keep < 0:
            raise ValueError("features.column_weighting.keep は 0 以上にしてください（0 なら全部の列）")
        if self.k < 1 or self.min_unit_rows < 1:
            raise ValueError("similarity.k と unit.min_rows は 1 以上にしてください")
        if not self.train_first_year < self.first_year <= self.last_year:
            raise ValueError("evaluation は train_first_year < first_year <= last_year にしてください")
        if not self.first_year - 1 <= self.tune_last_year <= self.last_year:
            raise ValueError("evaluation の tune_last_year は first_year − 1 から last_year までにしてください")

    @classmethod
    def load(cls, path: Path | None = None) -> BuyOrFadeSettings:
        """初期値に ``path`` のファイルの項目を重ねた方針。``path`` が None なら初期値のまま。"""
        defaults = SettingsFile(DEFAULT_SETTINGS_PATH).read()
        overrides = SettingsFile(path).read() if path is not None else {}
        SettingsNameCheck(defaults).check(overrides, str(path))
        return cls.from_toml(SettingsOverlay(defaults).apply(overrides))

    @classmethod
    def from_toml(cls, values: Mapping[str, Any]) -> BuyOrFadeSettings:
        """設定ファイルの形（表ごとの辞書）から作る。"""
        unit, features, stake, evaluation = values["unit"], values["features"], values["stake"], values["evaluation"]
        weighting = features["column_weighting"]
        return cls(
            min_unit_rows=int(unit["min_rows"]),
            unit_split=str(unit["split"]),
            timing=PredictionTiming.parse(features["timing"]),
            excluded_features=tuple(features["exclude"]),
            add_missing_flags=bool(features["add_missing_flags"]),
            scaling=str(features["scaling"]),
            categorical_encoding=str(features["categorical"]),
            group_weights={name: float(weight) for name, weight in features["group_weights"].items()},
            column_weighting=str(weighting["method"]),
            column_weighting_keep=int(weighting["keep"]),
            k=int(values["similarity"]["k"]),
            fade_margin=float(values["decision"]["fade_margin"]),
            win_margin=float(values["decision"]["win_margin"]),
            win_and_place_win_stake=int(stake["win_and_place_win"]),
            win_and_place_place_stake=int(stake["win_and_place_place"]),
            place_only_place_stake=int(stake["place_only_place"]),
            train_first_year=int(evaluation["train_first_year"]),
            first_year=int(evaluation["first_year"]),
            last_year=int(evaluation["last_year"]),
            tune_last_year=int(evaluation["tune_last_year"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """モデルと一緒に保存する形（JSON にできる辞書）。"""
        values = asdict(self)
        values["timing"] = self.timing.value
        values["excluded_features"] = list(self.excluded_features)
        values["group_weights"] = dict(self.group_weights)
        return values

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> BuyOrFadeSettings:
        """``to_dict`` で保存した形から作る。

        あとから足した項目（``tune_last_year``、単位の分け方、そろえ方、カテゴリの直し方、列ごとの重み）が無い
        古い一式は、足す前と同じ作り方になる値で読む（``tune_last_year`` は、全部の年を方針を決める年とみなす）。
        """
        return cls(**{
            "tune_last_year": values["last_year"], **_ADDED_LATER,
            **values, "timing": PredictionTiming.parse(values["timing"]),
            "excluded_features": tuple(values["excluded_features"]),
        })

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _check_choice(name: str, value: str, choices: Sequence[str]) -> None:
    """名前で選ぶ項目の値が、書ける値のどれかでなければ ``ValueError``。"""
    if value not in choices:
        raise ValueError(f"{name} は {'・'.join(choices)} のどれかにしてください（{value}）")
