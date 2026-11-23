"""rid（16桁）から、ばんえい（帯広）のレースかを見分ける。"""

from __future__ import annotations

from 共通.local_codes import BANEI_VENUE_CODE

#: rid の中の競馬場コードの位置（開催年4桁＋開催月日4桁のあと）。
_VENUE = slice(8, 10)


def is_banei(rid: str) -> bool:
    return rid[_VENUE] == BANEI_VENUE_CODE
