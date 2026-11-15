"""オッズの動きの直しの重みを、ファイルに書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path

from ..odds_move import OddsMoveWeights

#: 置き場所のファイル名（モデルの置き場所の直下）。
FILE_NAME = "odds_move.json"


class OddsMoveWeightsRepository:
    """目的（3着以内・1着）ごとの直しの重み（``OddsMoveWeights``）を ``<root>/odds_move.json`` に書く・読む。

    重みは JV-Data のオッズと結果から学んだ値なので、組の確率の重み（``ComboBlendWeightsRepository``）と同じく、Git の対象外の
    reports/ の下のモデルの置き場所に置く。ファイルの形は ``{"3着以内": {"切片": …, …}, "1着": {…}}``。
    """

    def __init__(self, root: Path) -> None:
        self._path = Path(root) / FILE_NAME

    @property
    def path(self) -> Path:
        return self._path

    def save(self, weights: dict[str, OddsMoveWeights]) -> Path:
        saved = {target: value.to_dict() for target, value in weights.items()}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_bytes((json.dumps(saved, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return self._path

    def load(self) -> dict[str, OddsMoveWeights]:
        """保存した重み。まだ無ければ空の辞書（確率を直さない）。"""
        if not self._path.exists():
            return {}
        saved = json.loads(self._path.read_text(encoding="utf-8"))
        return {target: OddsMoveWeights.from_dict(value) for target, value in saved.items()}
