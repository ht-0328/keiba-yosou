"""帯狙いで選べる買い方。"""

from __future__ import annotations

from yosou.upset_premise.betting import DEFAULT_FLAT_STAKE_YEN, FlatPlan, FormationPlan, ObiStakePlan, TicketPlan

#: 買い方の短い名前 → 説明（研究「百万馬券を当てる」の docs/01 の 6 と docs/06）。
PLAN_LABELS: dict[str, str] = {
    "一律": "1,000倍以上の組を組の確率の高い順に一律の金額で（3連単）",
    "甲": "全部帯（3連単）", "乙": "本線厚め（3連単）", "丙": "全部帯（3連複）",
}
#: 既定の買い方。研究「百万馬券を当てる」の docs/06 で、1,000倍以上のレースを当てる割合が甲・乙・丙より高かった一律にする。
DEFAULT_PLAN = "一律"


def plan_named(key: str, stake_yen: int = DEFAULT_FLAT_STAKE_YEN) -> TicketPlan:
    """短い名前から買い方を作る。``stake_yen`` は一律の1点の金額（ほかの買い方は使わない）。知らない名前は ``ValueError``。"""
    if key == "一律":
        return FlatPlan(stake_yen)
    plans: dict[str, TicketPlan] = {"甲": ObiStakePlan(ordered=True), "乙": FormationPlan(), "丙": ObiStakePlan(ordered=False)}
    if key not in plans:
        raise ValueError(f"知らない買い方です: {key}（{' / '.join(PLAN_LABELS)}）")
    return plans[key]
