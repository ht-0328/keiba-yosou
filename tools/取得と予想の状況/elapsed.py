"""時刻の差を「3時間前」「あと12分」のような文字にする（関数だけ）。"""

from __future__ import annotations

from datetime import datetime

_MINUTE, _HOUR, _DAY = 60, 3600, 86400


def ago_text(now: datetime, then: datetime | None) -> str:
    """``then`` が今からどれだけ前か。無ければ空。未来なら「これから」。"""
    if then is None:
        return ""
    seconds = int((now - then).total_seconds())
    if seconds < 0:
        return "これから"
    if seconds < _MINUTE:
        return "今"
    if seconds < _HOUR:
        return f"{seconds // _MINUTE}分前"
    if seconds < _DAY:
        return f"{seconds // _HOUR}時間前"
    return f"{seconds // _DAY}日前"


def until_text(now: datetime, then: datetime | None) -> str:
    """``then`` まであとどれだけか。無ければ空。過ぎていれば「済み」。"""
    if then is None:
        return ""
    seconds = int((then - now).total_seconds())
    if seconds < 0:
        return "済み"
    if seconds < _HOUR:
        return f"あと{max(1, seconds // _MINUTE)}分"
    return f"あと{seconds // _HOUR}時間{(seconds % _HOUR) // _MINUTE}分"


def clock_text(moment: datetime | None) -> str:
    """``10/04 11:44`` の形。無ければ空。"""
    return moment.strftime("%m/%d %H:%M") if moment else ""


def stamp_text(moment: datetime | None) -> str:
    """``2026-10-04 11:44`` の形。無ければ空。"""
    return moment.strftime("%Y-%m-%d %H:%M") if moment else ""
