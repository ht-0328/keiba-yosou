"""調べる理論ごとの、事例の型の一覧。"""

from __future__ import annotations

from ..pace import HIGH, PACE, SLOW, WINNER_STYLE
from .case_pattern import CasePattern

#: 前に行く脚質と、後ろから行く脚質（JV-Data の脚質判定）。
FRONT, BACK = ("逃げ", "先行"), ("差し", "追込")
#: 逃げそうな馬（推定脚質が逃げ）の頭数の線。
FEW_LEADERS, MANY_LEADERS = 1, 3
#: 理論との関係。
AGREES, CONTRADICTS = "理論どおり", "理論に反する"

PATTERNS: tuple[CasePattern, ...] = (
    CasePattern("slow_front", "スローで前（逃げ・先行）が勝った", AGREES,
                lambda r: (r[PACE] == SLOW) & r[WINNER_STYLE].isin(FRONT)),
    CasePattern("slow_back", "スローで後ろ（差し・追込）が勝った", CONTRADICTS,
                lambda r: (r[PACE] == SLOW) & r[WINNER_STYLE].isin(BACK)),
    CasePattern("high_back", "ハイで後ろ（差し・追込）が勝った", AGREES,
                lambda r: (r[PACE] == HIGH) & r[WINNER_STYLE].isin(BACK)),
    CasePattern("high_front", "ハイで前（逃げ・先行）が勝った", CONTRADICTS,
                lambda r: (r[PACE] == HIGH) & r[WINNER_STYLE].isin(FRONT)),
    CasePattern("few_leaders_high", f"逃げそうな馬が{FEW_LEADERS}頭以下なのにハイ", CONTRADICTS,
                lambda r: (r["lead_candidates"] <= FEW_LEADERS) & (r[PACE] == HIGH)),
    CasePattern("many_leaders_slow", f"逃げそうな馬が{MANY_LEADERS}頭以上なのにスロー", CONTRADICTS,
                lambda r: (r["lead_candidates"] >= MANY_LEADERS) & (r[PACE] == SLOW)),
)
