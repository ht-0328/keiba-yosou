"""帯狙いで選べる買い方（定数だけ）。"""

from __future__ import annotations

from yosou.upset_premise.betting import FormationPlan, ObiStakePlan, TicketPlan

#: 買い方の短い名前 → 買い方（研究「百万馬券を当てる」の docs/01 の 6）。
PLANS: dict[str, TicketPlan] = {"甲": ObiStakePlan(ordered=True), "乙": FormationPlan(), "丙": ObiStakePlan(ordered=False)}
#: 既定の買い方。研究「百万馬券を当てる」の docs/04 では、どの買い方も採用の基準に届かなかった。
#: 既定は、当たれば必ず帯になる甲にする（帯を当てるという狙いにいちばん合う買い方のため）。
DEFAULT_PLAN = "甲"
