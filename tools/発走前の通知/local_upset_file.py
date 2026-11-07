"""地方の1レースの「券種ごとの中荒れ以上の確率」のファイル（``<rid>.荒れ具合.json``）の読み書き。"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

#: ファイルの中身の鍵（確率と、出せなかった理由）。
PROBABILITIES = "中荒れ以上の確率"
REASON = "理由"


class LocalUpsetFile:
    """書くのは発走前の予想（``local_predict.py``。予想と同じ接続で出す）、読むのは推奨買目（``SavedUpsetProbabilities``）。
    確率が出せなかったときは理由を書く。``read`` は、ファイルが無ければ ``FileNotFoundError``、理由が書いてあれば ``ValueError``、
    要る券種が無ければ ``LookupError``（推奨買目はどれでも、その券種だけを対象外にして理由を添える）。"""

    def clear(self, path: Path) -> None:
        """前に書いた中身を消す（予想し直すときに、古い確率を読まないように）。"""
        Path(path).unlink(missing_ok=True)

    def write(self, path: Path, probabilities: Mapping[str, float]) -> None:
        self._dump(path, {PROBABILITIES: {ticket: float(value) for ticket, value in probabilities.items()}})

    def write_reason(self, path: Path, reason: str) -> None:
        self._dump(path, {REASON: reason})

    def read(self, path: Path, tickets: Sequence[str]) -> dict[str, float]:
        """券種 → 中荒れ以上の確率（``tickets`` の券種だけ）。"""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"荒れ具合の予想のファイルがありません（{path.name}）")
        saved = json.loads(path.read_text(encoding="utf-8"))
        if REASON in saved:
            raise ValueError(saved[REASON])
        probabilities = saved[PROBABILITIES]
        missing = [ticket for ticket in tickets if ticket not in probabilities]
        if missing:
            raise LookupError(f"{'・'.join(missing)} の荒れ具合の予想がありません")
        return {ticket: float(probabilities[ticket]) for ticket in tickets}

    @staticmethod
    def _dump(path: Path, content: dict) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
