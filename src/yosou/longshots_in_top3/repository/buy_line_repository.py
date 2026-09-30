"""時点ごと・区分ごとの「買い」の線を、ファイルに書く・読む。"""

from __future__ import annotations

import json
import math
from pathlib import Path

from yosou.shared.feature import PredictionTiming

#: 置き場所のファイル名（モデルの置き場所の直下。複勝の見込みの倍率 ``place_price.json`` の隣）。
FILE_NAME = "buy_lines.json"


class BuyLineRepository:
    """時点 → 区分 → 複勝の期待値の線 を ``<root>/buy_lines.json`` に書く・読む（設計書 16 の 3）。

    学習のときに検証期間で決めた線を、モデルと一緒に置き、予測のときに「買い」の印を付けるのに使う。
    線を決められなかった区分（検証期間で 100% を超える線が無かった）は書かない（その区分には印を付けない）。
    SQL ではなくファイルに読み書きする（``PlacePriceRepository`` と同じく reports/ の下に置く）。
    """

    def __init__(self, root: Path) -> None:
        self._path = Path(root) / FILE_NAME

    def save(self, lines: dict[PredictionTiming, dict[str, float]]) -> Path:
        written = {timing.value: {zone: value for zone, value in zones.items() if not math.isnan(value)}
                   for timing, zones in lines.items()}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(written, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self._path

    def load(self) -> dict[PredictionTiming, dict[str, float]]:
        """保存した線。まだ無ければ（前の版で学習したモデル）空。"""
        if not self._path.exists():
            return {}
        saved = json.loads(self._path.read_text(encoding="utf-8"))
        return {PredictionTiming(timing): {zone: float(value) for zone, value in zones.items()}
                for timing, zones in saved.items()}
