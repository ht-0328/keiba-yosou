"""区切りごとの組の確率の重みを、ファイルに書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboBlendWeights


class FoldWeightsFile:
    """区切りの名前 → 券種 → 重み（``ComboBlendWeights``）を、1つの JSON（``{"2019年前半": {"馬連": {...}, ...}, ...}``）に書く・読む。

    区切りごとに書き足すので、途中で止めても済んだ区切りは残る。重みは JV-Data から推定した値なので、Git の対象外の reports/ に置く。
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def has(self, fold: str) -> bool:
        return fold in self._saved()

    def save(self, fold: str, weights: dict[TicketType, ComboBlendWeights]) -> None:
        saved = self._saved()
        saved[fold] = {ticket_type.label: value.to_dict() for ticket_type, value in weights.items()}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(saved, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def load(self) -> dict[str, dict[TicketType, ComboBlendWeights]]:
        return {fold: {TicketType.parse(label): ComboBlendWeights.from_dict(value) for label, value in by_type.items()}
                for fold, by_type in self._saved().items()}

    def _saved(self) -> dict:
        return json.loads(self._path.read_text(encoding="utf-8")) if self._path.exists() else {}
