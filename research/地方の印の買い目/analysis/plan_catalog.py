"""比べる買い方の一覧。"""

from __future__ import annotations

from .mark_plan import PER_RACE, MarkPlan
from .reverse_combos import REVERSE_RULE

WIN, WIDE, QUINELLA, EXACTA = "単勝", "ワイド", "馬連", "馬単"
TRIO, TRIFECTA = "3連複（◎−○▲☆−○▲△☆）", "3連単（◎→○▲☆→○▲△☆）"
#: 印で組む買い方の全部（中央の元の6つと馬単の裏）。
ALL_RULES: tuple[str, ...] = (WIN, WIDE, QUINELLA, EXACTA, REVERSE_RULE, TRIO, TRIFECTA)
#: 中央の印の買い目と同じ組（単勝・馬連・馬単・馬単の裏・3連単）。
JRA_RULES: tuple[str, ...] = (WIN, QUINELLA, EXACTA, REVERSE_RULE, TRIFECTA)
#: 地方で採る組（単体で各年 100% を割る馬連・馬単の裏を外したもの）。
LOCAL_RULES: tuple[str, ...] = (WIN, EXACTA, TRIFECTA)
#: 比べる組（地方で採る組にワイドを足したもの）。
LOCAL_WITH_WIDE: tuple[str, ...] = (WIN, WIDE, EXACTA, TRIFECTA)


def plan_catalog() -> tuple[MarkPlan, ...]:
    """1. 印どおり（全部の点）と、点ごとの期待値 1.0 以上を買い方ごとに。2. レースごと（見込みの回収率 1.0 以上）を買い方ごとと組で。
    3. 地方で採る組の線（1.1・1.2）と頭数（8頭・11頭以上）を動かして、結論が崩れないかを見る。"""
    plans: list[MarkPlan] = []
    for rule in ALL_RULES:
        plans.append(MarkPlan(f"{rule}・印どおり", (rule,)))
        plans.append(MarkPlan(f"{rule}・期待値 1.0 以上の点", (rule,), ev_min=1.0))
    plans += [MarkPlan(f"{rule}・レースごと 見込み 1.0 以上", (rule,), PER_RACE) for rule in ALL_RULES]
    plans += [MarkPlan(f"{label}・レースごと 見込み 1.0 以上", rules, PER_RACE)
              for label, rules in (("中央と同じ組（単勝・馬連・馬単・裏・3連単）", JRA_RULES), ("全部の買い方", ALL_RULES),
                                   ("単勝・ワイド・馬単・3連単", LOCAL_WITH_WIDE), ("単勝・馬単・3連単", LOCAL_RULES))]
    plans += [MarkPlan(f"単勝・馬単・3連単・レースごと 見込み {line:.1f} 以上", LOCAL_RULES, PER_RACE, line=line) for line in (1.1, 1.2)]
    plans += [MarkPlan(f"単勝・馬単・3連単・レースごと 見込み 1.0 以上・{heads}頭以上", LOCAL_RULES, PER_RACE, min_heads=heads) for heads in (8, 11)]
    return tuple(plans)
