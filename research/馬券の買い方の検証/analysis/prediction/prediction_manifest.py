"""一括予測の記録（manifest.json）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

#: 記録のファイルの名前（予測の CSV と同じフォルダに置く）。
MANIFEST_NAME = "manifest.json"


@dataclass
class PredictionManifest:
    """いつ・どの期間・どの時点・どのモデルで予測を出したかの記録。あとで結果を見るときに、予測の出どころを確かめるためのもの。"""

    first_day: date
    last_day: date
    timing: str
    run_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    entries: list[dict[str, object]] = field(default_factory=list)

    def add(self, name: str, file: Path, models_root: Path, rows: int, races: int) -> None:
        """1モデルぶんの記録を足す。"""
        self.entries.append({
            "name": name, "file": str(file), "models": str(models_root), "rows": rows, "races": races,
        })

    def to_dict(self) -> dict[str, object]:
        return {
            "run_at": self.run_at, "first_day": self.first_day.isoformat(), "last_day": self.last_day.isoformat(),
            "timing": self.timing, "entries": list(self.entries),
        }

    def write(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> PredictionManifest:
        saved = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            date.fromisoformat(saved["first_day"]), date.fromisoformat(saved["last_day"]), saved["timing"],
            run_at=saved["run_at"], entries=list(saved["entries"]),
        )
