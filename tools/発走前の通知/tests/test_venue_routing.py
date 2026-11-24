"""競馬場での振り分け（VenueRoutedRunner・VenueRoutedMessage・VenueRoutedStore）のテスト。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.venue_route import is_banei
from 発走前の通知.venue_routed_message import VenueRoutedMessage
from 発走前の通知.venue_routed_runner import VenueRoutedRunner
from 発走前の通知.venue_routed_store import VenueRoutedStore

_BANEI = "2026112383170309"
_LOCAL = "2026112347150401"


class _Part:
    """予想・文・保存先のどれにもなる、呼ばれたことを覚えるだけの部品。"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[str] = []

    def run_day(self, day: str) -> None:
        self.calls.append(f"day {day}")

    def run_race(self, rid: str, day: str) -> None:
        self.calls.append(rid)

    def log_path(self, day: str) -> Path:
        return Path(self.name)

    def build(self, rid: str) -> RaceNotice:
        return RaceNotice(text=self.name)

    def saved_at(self, rid: str) -> datetime | None:
        return datetime(2026, 11, 23, 18, 0 if self.name == "地方" else 1)


def test_ばんえいは競馬場コード83() -> None:
    assert is_banei(_BANEI) and not is_banei(_LOCAL)


def test_予想はレースの競馬場で振り分け_朝の準備は両方() -> None:
    local, banei = _Part("地方"), _Part("ばんえい")
    runner = VenueRoutedRunner(local, banei)
    runner.run_day("2026-11-23")
    runner.run_race(_BANEI, "2026-11-23")
    runner.run_race(_LOCAL, "2026-11-23")
    assert local.calls == ["day 2026-11-23", _LOCAL]
    assert banei.calls == ["day 2026-11-23", _BANEI]
    assert runner.log_path("2026-11-23") == Path("地方")


def test_文と保存先もレースの競馬場で振り分ける() -> None:
    local, banei = _Part("地方"), _Part("ばんえい")
    message = VenueRoutedMessage(local, banei)
    assert (message.build(_BANEI).text, message.build(_LOCAL).text) == ("ばんえい", "地方")
    store = VenueRoutedStore(local, banei)
    assert (store.saved_at(_BANEI).minute, store.saved_at(_LOCAL).minute) == (1, 0)
