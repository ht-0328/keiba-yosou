"""時点ごと・人気帯ごとの危険度の線を、ファイルに書く・読む。"""

from __future__ import annotations

import json
import math
from pathlib import Path

from yosou.shared.feature import PredictionTiming

#: 置き場所のファイル名（モデルの置き場所の直下）。
FILE_NAME = "danger_thresholds.json"


class DangerThresholdRepository:
    """時点 → 人気帯 → 危険度の線 を ``<root>/danger_thresholds.json`` に書く・読む。

    学習のときに検証期間で決めた線を、モデルと一緒に置き、予測のときに「危険」を判定するのに使う。
    線を決められなかった人気帯（危険とする馬が少なすぎた）は書かない（その人気帯は危険と判定しない）。
    """

    def __init__(self, root: Path) -> None:
        self._path = Path(root) / FILE_NAME

    def save(self, thresholds: dict[PredictionTiming, dict[str, float]]) -> Path:
        written = {timing.value: {band: value for band, value in bands.items() if not math.isnan(value)}
                   for timing, bands in thresholds.items()}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(written, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self._path

    def load(self) -> dict[PredictionTiming, dict[str, float]]:
        """保存した線。まだ無ければ（前の版で学習したモデル）空。"""
        if not self._path.exists():
            return {}
        saved = json.loads(self._path.read_text(encoding="utf-8"))
        return {PredictionTiming(timing): {band: float(value) for band, value in bands.items()}
                for timing, bands in saved.items()}
