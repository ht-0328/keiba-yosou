"""この予想の方針（設定ファイルの中身）。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from yosou.shared.feature import PredictionTiming
from yosou.shared.setting.settings_file import SettingsFile
from yosou.shared.setting.settings_name_check import SettingsNameCheck
from yosou.shared.setting.settings_overlay import SettingsOverlay

#: この予想の初期値の設定ファイル。
DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "default_settings.toml"
#: 予測に使える時点。木曜は人気が分からないので使えない。
_TIMINGS = (PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY)


@dataclass(frozen=True)
class BuyOrFadeSettings:
    """方針の値（設計書 14）。項目の意味は ``default_settings.toml`` のコメントにある。

    ``load()`` で、初期値のファイルに利用者のファイルを重ねて作る。学習したモデルと一緒に保存し、
    予測のときに同じ方針を使う（``to_dict``・``from_dict``）。
    """

    min_unit_rows: int
    timing: PredictionTiming
    excluded_features: tuple[str, ...]
    add_missing_flags: bool
    group_weights: Mapping[str, float]
    k: int
    fade_margin: float
    win_margin: float
    win_and_place_win_stake: int
    win_and_place_place_stake: int
    place_only_place_stake: int
    train_first_year: int
    first_year: int
    last_year: int

    def __post_init__(self) -> None:
        if self.timing not in _TIMINGS:
            raise ValueError(f"features.timing は 前日 か 当日 にしてください（{self.timing.label}では人気が分かりません）")
        if self.k < 1 or self.min_unit_rows < 1:
            raise ValueError("similarity.k と unit.min_rows は 1 以上にしてください")
        if not self.train_first_year < self.first_year <= self.last_year:
            raise ValueError("evaluation は train_first_year < first_year <= last_year にしてください")

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
        features, stake, evaluation = values["features"], values["stake"], values["evaluation"]
        return cls(
            min_unit_rows=int(values["unit"]["min_rows"]),
            timing=PredictionTiming.parse(features["timing"]),
            excluded_features=tuple(features["exclude"]),
            add_missing_flags=bool(features["add_missing_flags"]),
            group_weights={name: float(weight) for name, weight in features["group_weights"].items()},
            k=int(values["similarity"]["k"]),
            fade_margin=float(values["decision"]["fade_margin"]),
            win_margin=float(values["decision"]["win_margin"]),
            win_and_place_win_stake=int(stake["win_and_place_win"]),
            win_and_place_place_stake=int(stake["win_and_place_place"]),
            place_only_place_stake=int(stake["place_only_place"]),
            train_first_year=int(evaluation["train_first_year"]),
            first_year=int(evaluation["first_year"]),
            last_year=int(evaluation["last_year"]),
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
        """``to_dict`` で保存した形から作る。"""
        return cls(**{
            **values, "timing": PredictionTiming.parse(values["timing"]),
            "excluded_features": tuple(values["excluded_features"]),
        })

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
