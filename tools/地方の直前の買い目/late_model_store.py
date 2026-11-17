"""学んだ2つのモデルの置き場所（フォルダ）。``fit.py`` が書き、買い目を決めるときに読む。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import lightgbm as lgb

from .late_models import LateModels

#: 既定の置き場所（Git 対象外）。
PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_FOLDER = PROJECT / "reports" / "地方の直前の買い目" / "models"
_META = "meta.json"
_LIKENESS = "買う馬らしさ"
_PAYBACK = "戻りの見込み"


class LateModelStore:
    """モデルは ``買う馬らしさ-<番号>.txt``・``戻りの見込み-<番号>.txt``（LightGBM の文字の形式）、学んだ条件は ``meta.json``。
    無ければ ``FileNotFoundError``。"""

    def __init__(self, folder: Path = DEFAULT_FOLDER) -> None:
        self._folder = folder

    @property
    def folder(self) -> Path:
        return self._folder

    def save(self, models: LateModels, meta: dict[str, Any]) -> Path:
        self._folder.mkdir(parents=True, exist_ok=True)
        for name, boosters in ((_LIKENESS, models.likeness), (_PAYBACK, models.payback)):
            for old in self._folder.glob(f"{name}-*.txt"):
                old.unlink()
            for index, booster in enumerate(boosters):
                (self._folder / f"{name}-{index}.txt").write_text(booster.model_to_string(), encoding="utf-8")
        (self._folder / _META).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return self._folder

    def load(self) -> LateModels:
        likeness = self._boosters(_LIKENESS)
        payback = self._boosters(_PAYBACK)
        if not likeness or not payback:
            raise FileNotFoundError(f"直前の買い目のモデルがありません: {self._folder}。先に tools/地方の直前の買い目/fit.py で学んでください")
        return LateModels(likeness, payback)

    def meta(self) -> dict[str, Any]:
        path = self._folder / _META
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def _boosters(self, name: str) -> tuple[lgb.Booster, ...]:
        paths = sorted(self._folder.glob(f"{name}-*.txt"))
        return tuple(lgb.Booster(model_str=path.read_text(encoding="utf-8")) for path in paths)
