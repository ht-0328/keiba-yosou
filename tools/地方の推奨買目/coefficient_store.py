"""当てはめた条件つきロジットの係数の置き場所（JSON）。``fit.py`` が書き、推奨買目を出すときに読む。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .position_coefficients import PositionCoefficients

#: 既定の置き場所（Git 対象外）。
PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = PROJECT / "reports" / "地方の推奨買目" / "係数.json"


class CoefficientStore:
    """``save`` は係数と当てはめの条件（``meta``）を1つの JSON に、``load`` は係数だけを返す。無ければ ``FileNotFoundError``。"""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def save(self, coefficients: PositionCoefficients, meta: dict[str, Any]) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        body = {"first": coefficients.first, "second": coefficients.second, "third": coefficients.third, "meta": meta}
        self._path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
        return self._path

    def load(self) -> PositionCoefficients:
        body = self._read()
        return PositionCoefficients(dict(body["first"]), dict(body["second"]), dict(body["third"]))

    def meta(self) -> dict[str, Any]:
        return dict(self._read().get("meta", {}))

    def _read(self) -> dict[str, Any]:
        if not self._path.is_file():
            raise FileNotFoundError(f"係数がありません: {self._path}。先に tools/地方の推奨買目/fit.py で当てはめてください")
        return json.loads(self._path.read_text(encoding="utf-8"))
