"""枠連の組の確率の重みを、ファイルに書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path

from ..combo_value.bracket_blend_weights import BracketBlendWeights

#: 置き場所のファイル名（モデルの置き場所の直下）。
FILE_NAME = "bracket_blend.json"


class BracketBlendWeightsRepository:
    """枠連の組の確率の重み（``BracketBlendWeights``）を ``<root>/bracket_blend.json`` に書く・読む。

    ほかの券種の重み（``ComboBlendWeightsRepository`` の ``combo_blend.json``）と、もとの数と名前が違うので別のファイルにする。
    JV-Data のオッズと払戻から推定した値なので、Git の対象外の reports/ の下のモデルの置き場所に置く。
    """

    def __init__(self, root: Path) -> None:
        self._path = Path(root) / FILE_NAME

    @property
    def path(self) -> Path:
        return self._path

    def save(self, weights: BracketBlendWeights) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(weights.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self._path

    def load(self) -> BracketBlendWeights | None:
        """保存した重み。まだ無ければ None（枠連の組の期待値の買い目は作らない）。"""
        if not self._path.exists():
            return None
        return BracketBlendWeights.from_dict(json.loads(self._path.read_text(encoding="utf-8")))
