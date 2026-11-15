"""地方の印の買い目の買い方（設計書「買うレースと買い目を決める」の 12）。

研究「地方の印の買い目」で、地方の組の確率で期待値を付け、1レースの見込みの回収率で買うかを決めると、2024〜2026年の各年で回収率 100% を超えた組。
中央の印の買い目（``MARK_VALUE_LABELS``）のうち、馬連と馬単の裏は、地方では単体で 100% を割る年があるので入れない。
"""

from __future__ import annotations

from 今週の予想.ticket_rules import BET_RULES, TicketRule

#: 採る買い方の名前（中央の ``BET_RULES`` の名前と同じ）。
_ADOPTED: tuple[str, ...] = ("単勝", "馬単", "3連単（◎→○▲☆→○▲△☆）")
#: 印の位置で組む買い方（単勝 ◎・馬単 ◎→○▲☆・3連単 ◎→○▲☆→○▲△☆）。
LOCAL_MARK_RULES: tuple[TicketRule, ...] = tuple(rule for rule in BET_RULES if isinstance(rule, TicketRule) and rule.label in _ADOPTED)
LOCAL_MARK_LABELS: tuple[str, ...] = tuple(rule.label for rule in LOCAL_MARK_RULES)
#: 出す最少の頭数（研究で確かめた範囲）。
MARK_MIN_HEADS = 5
