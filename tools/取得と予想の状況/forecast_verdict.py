"""1レースの予想の判定（種類・理由・作ってある予想の要約）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from 取得と予想の状況.verdict_kind import VerdictKind


@dataclass(frozen=True)
class ForecastVerdict:
    """``ForecastCheck`` の結果。``current_timing`` は今の DB で選ぶ時点、``saved_timing`` は作ってある予想の時点（無ければ None）。
    ``marks`` は作ってある予想の印（``◎3 ○7 …``）、``grades`` はレースの的中率・配当率の1行（``的中率 B（38%）・配当率 A（56%）``。目安を出す前の版の結果なら空）。
    """

    kind: VerdictKind
    detail: str
    current_timing: str
    saved_timing: str | None = None
    made_at: datetime | None = None
    marks: str = ""
    grades: str = ""

    @property
    def label(self) -> str:
        """``時点が進んだ（前日 → 当日）`` のような1語。"""
        return f"{self.kind.value}（{self.detail}）" if self.detail else self.kind.value

    @property
    def is_saved(self) -> bool:
        """予想が作ってあるか。"""
        return self.saved_timing is not None
