"""学んだモデルの置き場所（フォルダ）。``fit.py`` が書き、買い目を決めるときに読む。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
from catboost import CatBoostClassifier

from .final_models import TARGETS, FinalModels

#: 既定の置き場所（Git 対象外）。
PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_FOLDER = PROJECT / "reports" / "高知ファイナルの買い目" / "models"
_META = "meta.json"
#: meta.json の、単勝人気ごとの 3着以内率（騎手の材料に使う）の鍵。
POPULARITY_RATES = "単勝人気ごとの3着以内率"


class FinalModelStore:
    """LightGBM は ``<目的>-<番号>.txt``、CatBoost は ``<目的>.cbm``、学んだ条件は ``meta.json``。無ければ ``FileNotFoundError``。"""

    def __init__(self, folder: Path = DEFAULT_FOLDER) -> None:
        self._folder = folder

    def save(self, models: FinalModels, meta: dict[str, Any]) -> Path:
        self._folder.mkdir(parents=True, exist_ok=True)
        for target in TARGETS:
            for old in self._folder.glob(f"{target}-*.txt"):
                old.unlink()
            for index, booster in enumerate(models.boosters[target]):
                (self._folder / f"{target}-{index}.txt").write_text(booster.model_to_string(), encoding="utf-8")
            models.cats[target].save_model(str(self._folder / f"{target}.cbm"))
        (self._folder / _META).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return self._folder

    def load(self) -> FinalModels:
        boosters = {target: self._boosters(target) for target in TARGETS}
        paths = {target: self._folder / f"{target}.cbm" for target in TARGETS}
        if not all(boosters.values()) or not all(path.is_file() for path in paths.values()):
            raise FileNotFoundError(f"高知ファイナルのモデルがありません: {self._folder}。先に tools/高知ファイナルの買い目/fit.py で学んでください")
        cats = {target: CatBoostClassifier().load_model(str(path)) for target, path in paths.items()}
        return FinalModels(boosters, cats)

    def meta(self) -> dict[str, Any]:
        path = self._folder / _META
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def popularity_rates(self) -> dict[float, float]:
        """学んだときに数えた、単勝人気 → 3着以内率。"""
        return {float(popularity): float(rate) for popularity, rate in self.meta().get(POPULARITY_RATES, {}).items()}

    def _boosters(self, target: str) -> tuple[lgb.Booster, ...]:
        paths = sorted(self._folder.glob(f"{target}-*.txt"))
        return tuple(lgb.Booster(model_str=path.read_text(encoding="utf-8")) for path in paths)
