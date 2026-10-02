"""段階の間で渡す戦略の JSON（探索 → 確認は chosen.json、確認 → 最後の1回は adopted.json）。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from .strategy import Round3Strategy


class StrategyListFile:
    """戦略の並びと記録（期間・基準の説明）を JSON に書き、次の段階で読み戻す。並びの順は、探索の順位のまま残す。"""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.exists()

    def write(self, strategies: Sequence[Round3Strategy], meta: dict[str, object] | None = None) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        body = {"meta": dict(meta or {}), "strategies": [strategy.to_dict() for strategy in strategies]}
        self._path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read(self) -> list[Round3Strategy]:
        """無ければ ``FileNotFoundError``。"""
        if not self._path.exists():
            raise FileNotFoundError(f"戦略のファイルがありません: {self._path}（先に前の段階を実行してください）")
        saved = json.loads(self._path.read_text(encoding="utf-8"))
        return [Round3Strategy.from_dict(item) for item in saved["strategies"]]

    def meta(self) -> dict[str, object]:
        """記録の部分。"""
        return dict(json.loads(self._path.read_text(encoding="utf-8")).get("meta", {}))
