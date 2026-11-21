"""高知ファイナルの1レースの買い目のファイル（``<rid>.高知ファイナル.json``）の読み書き。"""

from __future__ import annotations

import json
from pathlib import Path

from .final_bets import FinalBets


class FinalBetFile:
    """書くのは発走前の予想（``local_predict.py``）、読むのは通知の文。無ければ ``read`` は None（高知ファイナルでないレース）。"""

    def clear(self, path: Path) -> None:
        """前に書いた中身を消す（予想し直すときに、古い買い目を読まないように）。"""
        Path(path).unlink(missing_ok=True)

    def write(self, path: Path, bets: FinalBets) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bets.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")

    def read(self, path: Path) -> FinalBets | None:
        path = Path(path)
        return FinalBets.from_dict(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else None
