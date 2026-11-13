"""WIN5 の予想の記録（``reports/近走と適性からWIN5の買い目を決める/記録/<日>.json``）から、実際に使った1着の確率と締め切り前の単勝オッズを読む。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RECORDS = _PROJECT_ROOT / "reports" / "近走と適性からWIN5の買い目を決める" / "記録"


@dataclass(frozen=True)
class Win5RecordProbabilities:
    """区切りごとの予測が無い最近の WIN5 の日（例 2026-11-08）を補う。1行 = 1頭。
    列は race_id・horse_no・model（そろえた1着の確率）・record_odds（予想したときの締め切り前の単勝オッズ）。"""

    folder: Path = DEFAULT_RECORDS

    def load(self) -> pd.DataFrame:
        rows = list(chain.from_iterable(map(self._rows, sorted(Path(self.folder).glob("*.json")))))
        return pd.DataFrame(rows, columns=["race_id", "horse_no", "model", "record_odds"])

    def _rows(self, path: Path) -> list[dict[str, object]]:
        record = json.loads(path.read_text(encoding="utf-8"))
        return list(chain.from_iterable(map(self._leg_rows, record.get("対象レース", []))))

    @staticmethod
    def _leg_rows(leg: dict) -> list[dict[str, object]]:
        return [
            {"race_id": str(leg["レースID"]), "horse_no": float(horse["馬番"]), "model": float(horse["そろえた1着の確率"]),
             "record_odds": float(horse["単勝オッズ"])}
            for horse in leg.get("馬", [])
        ]
