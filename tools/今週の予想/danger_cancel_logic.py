"""AI＋ロジック予想の消のロジック: 1着の予想が市場の見立て以上の馬は、消を取り消す。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: 取り消す理由の文。
REASON = "1着の予想が市場の見立て以上"


class DangerCancelLogic:
    """``horse`` は予想の1頭（``is_danger``・``win_probability``・``market_win`` を見る）。

    消は「人気馬が4着以下になるか」の予想で決める。一方で、別のモデルの「1着の予想」（``win_probability``）が、
    その馬を市場の見立て（単勝オッズから見た勝率 ``market_win``）以上に見ていることがある。この2つが食い違う消は、過去のレースでよく勝っていた
    （研究「AIとロジックの予想」の docs/03）。そういう馬は消にしない。印と買い目は AI だけの予想のまま変えない。
    """

    def cancels(self, horse: Mapping[str, Any]) -> bool:
        """消を取り消すか。消でない馬・値の無い馬は取り消さない。"""
        if not horse.get("is_danger"):
            return False
        win, market = horse.get("win_probability"), horse.get("market_win")
        if win is None or market is None or win != win or market != market:
            return False
        return float(win) >= float(market)
