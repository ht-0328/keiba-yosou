"""選んだ戦略の JSON。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from .strategy import Strategy


class ChosenStrategiesFile:
    """探索で選んだ戦略を JSON に書き、確認のときに読み戻す。``meta`` には探索の期間や基準の説明を残す。"""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def write(self, strategies: Sequence[Strategy], meta: dict[str, object] | None = None) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        body = {"meta": dict(meta or {}), "strategies": [strategy.to_dict() for strategy in strategies]}
        self._path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read(self) -> list[Strategy]:
        if not self._path.exists():
            raise FileNotFoundError(f"選んだ戦略のファイルがありません: {self._path}（先に探索を実行してください）")
        saved = json.loads(self._path.read_text(encoding="utf-8"))
        return [Strategy.from_dict(item) for item in saved["strategies"]]
