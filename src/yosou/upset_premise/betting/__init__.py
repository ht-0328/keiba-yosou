"""第3段 買い目: 荒れる前提の予想から、1レース 1万円の3連単（と3連複）の買い目を組む（設計書 04 の 2）。

| 名前 | 仕事 |
|---|---|
| ``RaceHorses`` | 1レースの出走馬ごとの、1着の確率（レースで合計 1）と3着以内の確率（と今の予想の3着以内の確率） |
| ``TicketPlan`` | 買い方の決まり（インターフェース） |
| ``FlatPlan`` | 一律（3連単。既定）: 1,000倍以上の組を、組の確率の高い順に、一律の金額で予算に収まる点数だけ買う |
| ``ObiStakePlan`` | 甲（3連単）・丙（3連複）: 当たれば必ず帯になる組だけを、帯に要る金額で、予算に収まるまで買う |
| ``FormationPlan`` | 乙（3連単）: 1着3頭 → 2着5頭 → 3着8頭のフォーメーションで、組の確率の上位10点を厚くする |
| ``trifecta_probability``・``trio_probability`` | 1着の確率（と2着・3着の重み）から、組の確率を Harville の式で作る（関数） |
| ``betting_rules.py`` | 1レースの予算、1点の金額の単位と上限、一律の買い方の線と1点の金額の3パターン（定数だけ） |
"""

from .betting_rules import BIG_ODDS, DEFAULT_FLAT_STAKE_YEN, FLAT_STAKE_CHOICES, RACE_BUDGET_YEN, STAKE_MAX_YEN, STAKE_UNIT_YEN
from .flat_plan import FlatPlan
from .formation_plan import FormationPlan
from .harville import trifecta_probability, trio_probability
from .obi_stake_plan import ObiStakePlan
from .race_horses import RaceHorses
from .ticket_plan import TicketPlan

__all__ = [
    "RaceHorses", "TicketPlan", "FlatPlan", "ObiStakePlan", "FormationPlan", "trifecta_probability", "trio_probability",
    "RACE_BUDGET_YEN", "STAKE_UNIT_YEN", "STAKE_MAX_YEN", "BIG_ODDS", "DEFAULT_FLAT_STAKE_YEN", "FLAT_STAKE_CHOICES",
]
