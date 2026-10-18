"""組の確率の重み（券種ごと）を、ファイルに書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path

from ..betting import TicketType
from ..combo_value.combo_blend_weights import ComboBlendWeights

#: 置き場所のファイル名（モデルの置き場所の直下）。
FILE_NAME = "combo_blend.json"


class ComboBlendWeightsRepository:
    """券種ごとの組の確率の重み（``ComboBlendWeights``）を ``<root>/combo_blend.json`` に書く・読む。

    重みは JV-Data のオッズと払戻から推定した値なので、複勝の見込みの倍率（``PlacePriceRepository``）と同じく、Git の対象外の
    reports/ の下のモデルの置き場所に置く。ファイルの形は ``{"馬連": {"own": …, "trifecta": …, "harville": …, "ratio": …}, …}``。
    """

    def __init__(self, root: Path) -> None:
        self._path = Path(root) / FILE_NAME

    @property
    def path(self) -> Path:
        return self._path

    def save(self, weights: dict[TicketType, ComboBlendWeights]) -> Path:
        saved = {ticket_type.label: value.to_dict() for ticket_type, value in weights.items()}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self._path

    def load(self) -> dict[TicketType, ComboBlendWeights]:
        """保存した重み。まだ無ければ空の辞書（組の期待値で選ぶ買い目は作らない）。"""
        if not self._path.exists():
            return {}
        saved = json.loads(self._path.read_text(encoding="utf-8"))
        return {TicketType.parse(label): ComboBlendWeights.from_dict(value) for label, value in saved.items()}
