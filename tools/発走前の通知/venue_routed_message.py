"""レースの競馬場で、通知の文を作る部品を振り分ける（ばんえいは専用の文、ほかは地方の文）。"""

from __future__ import annotations

from 発走前の通知.day_notifier_protocols import Message
from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.venue_route import is_banei


class VenueRoutedMessage:
    def __init__(self, local: Message, banei: Message) -> None:
        self._local = local
        self._banei = banei

    def build(self, rid: str) -> RaceNotice:
        return (self._banei if is_banei(rid) else self._local).build(rid)
