"""レースの競馬場で、予想の保存先を振り分ける（ばんえいは専用の置き場所、ほかは地方の置き場所）。"""

from __future__ import annotations

from datetime import datetime

from 発走前の通知.day_notifier_protocols import SavedAt
from 発走前の通知.venue_route import is_banei


class VenueRoutedStore:
    def __init__(self, local: SavedAt, banei: SavedAt) -> None:
        self._local = local
        self._banei = banei

    def saved_at(self, rid: str) -> datetime | None:
        return (self._banei if is_banei(rid) else self._local).saved_at(rid)
