"""馬1頭の近走の文。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .run_line import RunLine


@dataclass(frozen=True)
class HorseStory:
    """馬1頭の近走の文。``lines`` は古い走から新しい走の順。``career_runs`` はその馬の中央での出走数（文にした走より多いことがある）。

    ``words`` は近走から付けた評価のことば（``EvaluationWords``。上向き・大敗続き。無ければ空）。
    """

    horse_id: str
    name: str
    lines: list[RunLine]
    career_runs: int
    words: list[str] = field(default_factory=list)
