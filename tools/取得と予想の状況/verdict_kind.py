"""1レースの予想が今の DB に対してどういう状態か（判定の種類）。"""

from __future__ import annotations

from enum import Enum


class VerdictKind(Enum):
    """判定の種類。値は画面と CLI に出す名前。"""

    MISSING = "未予想"
    FRESH = "最新"
    TIMING_ADVANCED = "時点が進んだ"
    VERSION_OLD = "作り方が古い"
    ODDS_NEWER = "オッズが新しい"
    FINISHED = "終了"
    CANCELLED = "中止"

    @property
    def needs_redo(self) -> bool:
        """予想し直すべきか（DB の方が予想より進んでいる）。"""
        return self in _REDO

    @property
    def tone(self) -> str:
        """画面の色分けの名前（ok / redo / missing / done）。"""
        return _TONES[self]


_REDO: frozenset[VerdictKind] = frozenset({VerdictKind.TIMING_ADVANCED, VerdictKind.VERSION_OLD, VerdictKind.ODDS_NEWER})
_TONES: dict[VerdictKind, str] = {
    VerdictKind.MISSING: "missing", VerdictKind.FRESH: "ok", VerdictKind.TIMING_ADVANCED: "redo", VerdictKind.VERSION_OLD: "redo",
    VerdictKind.ODDS_NEWER: "redo", VerdictKind.FINISHED: "done", VerdictKind.CANCELLED: "done",
}
