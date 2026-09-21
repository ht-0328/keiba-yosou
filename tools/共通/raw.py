"""元DB の生の値（仕様書の桁のままの文字列）を、表に出す数や文字にする。

レース詳細（``race``）と出馬表（``card``）が同じ読み方をするように、1か所に置く。
事実表（``facts``）は同じ変換を SQL の中で行う。ここは生の表を直接読む部品のためのもの。
"""

from __future__ import annotations

#: 馬体重の「無し」（未発表）と「計量不能」。
_NO_BODY_WEIGHT = ("000", "999")
#: タイム差の「無し」。
_NO_TIME_DIFF = "9999"
_POST_TIME_LENGTH = 4


def _is_positive_number(raw: str | None) -> bool:
    return bool(raw) and raw.strip().isdigit() and int(raw) != 0


def to_int(raw: str | None) -> int | None:
    """``'07'`` を 7 に。空・``'00'`` は None。"""
    return int(raw) if _is_positive_number(raw) else None


def tenths(raw: str | None) -> float | None:
    """``'350'`` を 35.0 に（10 倍の整数で入っている値）。空・0 は None。"""
    return int(raw) / 10.0 if _is_positive_number(raw) else None


def body_weight(weight: str | None, sign: str | None, diff: str | None) -> str:
    """``480(+2)`` の形。未発表・計量不能は空。"""
    if not _is_positive_number(weight) or weight in _NO_BODY_WEIGHT:
        return ""
    change = f"{sign}{int(diff)}" if sign in ("+", "-") and diff and diff.isdigit() else ("±0" if diff == "000" else "")
    return f"{int(weight)}({change})" if change else str(int(weight))


def race_time(raw: str | None) -> str:
    """``'1340'`` を ``1:34.0`` に。"""
    if not _is_positive_number(raw):
        return ""
    value = int(raw)
    return f"{value // 1000}:{(value % 1000) / 10:04.1f}"


def time_diff(raw: str | None) -> str:
    """``'+029'`` を ``+2.9`` に。1着は負の値。"""
    if not raw or not raw.strip() or raw == _NO_TIME_DIFF:
        return ""
    try:
        return f"{int(raw) / 10:+.1f}"
    except ValueError:
        return raw


def post_time(raw: str | None) -> str | None:
    """発走時刻 ``'1545'`` を ``15:45`` に。4桁でなければそのまま。"""
    if raw and len(raw) == _POST_TIME_LENGTH:
        return f"{raw[:2]}:{raw[2:]}"
    return raw
