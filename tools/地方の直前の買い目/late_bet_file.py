"""1レースの直前の買い目のファイル（``<rid>.直前.json``）の読み書き。"""

from __future__ import annotations

import json
from pathlib import Path

from .late_bets import LateBets


class LateBetFile:
    """書くのは発走前の予想（``local_predict.py``）、読むのは通知の文と成績の確かめ（``results.py``）。無ければ ``read`` は None。"""

    def clear(self, path: Path) -> None:
        """前に書いた中身を消す（予想し直すときに、古い買い目を読まないように）。"""
        Path(path).unlink(missing_ok=True)

    def write(self, path: Path, bets: LateBets) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bets.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")

    def read(self, path: Path) -> LateBets | None:
        path = Path(path)
        return LateBets.from_dict(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else None
