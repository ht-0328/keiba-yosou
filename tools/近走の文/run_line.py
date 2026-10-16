"""近走の文の1行。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .past_run import PastRun


@dataclass(frozen=True)
class RunLine:
    """1走の文（``sentence``）と、負けた走なら敗因の候補（``reasons``。無ければ空）。"""

    run: PastRun
    sentence: str
    reasons: list[str] = field(default_factory=list)
