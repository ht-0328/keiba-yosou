"""発走前の通知が書いた直前の買い目のファイル（``<開催日>/<rid>.直前.json``）を、期間で集める。"""

from __future__ import annotations

from pathlib import Path

from .late_bet_file import LateBetFile
from .late_bets import LateBets

#: 既定の置き場所（発走前の通知の地方の予想のフォルダ。Git 対象外）。
PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_FOLDER = PROJECT / "reports" / "発走前の通知" / "地方"
_SUFFIX = ".直前.json"


class SavedLateBets:
    """開催日のフォルダ名は YYYY-MM-DD。``read`` は（レースID, 直前の買い目）を開催日・レースID の順に返す。"""

    def __init__(self, folder: Path = DEFAULT_FOLDER, file: LateBetFile | None = None) -> None:
        self._folder = folder
        self._file = file or LateBetFile()

    def read(self, day_from: str, day_to: str) -> list[tuple[str, LateBets]]:
        """``day_from``〜``day_to``（YYYY-MM-DD。両端を含む）のファイル。"""
        days = sorted(path for path in self._folder.glob("????-??-??") if path.is_dir() and day_from <= path.name <= day_to)
        found: list[tuple[str, LateBets]] = []
        for day in days:
            for path in sorted(day.glob(f"*{_SUFFIX}")):
                bets = self._file.read(path)
                if bets is not None:
                    found.append((path.name.removesuffix(_SUFFIX), bets))
        return found
