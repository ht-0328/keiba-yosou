"""複勝の見込みの倍率（帯ごとの倍率）を、ファイルに書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: 置き場所のファイル名（モデルの置き場所の直下）。
FILE_NAME = "place_price.json"


class PlacePriceRepository:
    """複勝の見込みの倍率（``PlacePriceEstimator.state()`` の形の辞書）を ``<root>/place_price.json`` に書く・読む。

    学習データの期間の払戻で決めた倍率を、モデルと一緒に置き、予測のときに複勝の期待値を出すのに使う。
    SQL ではなくファイルに読み書きする（``ModelRepository`` と同じく reports/ の下に置く）。
    """

    def __init__(self, root: Path) -> None:
        self._path = Path(root) / FILE_NAME

    def save(self, state: dict[str, Any]) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self._path

    def load(self) -> dict[str, Any] | None:
        """保存した倍率。まだ無ければ（前の版で学習したモデル）None。"""
        if not self._path.exists():
            return None
        return json.loads(self._path.read_text(encoding="utf-8"))
