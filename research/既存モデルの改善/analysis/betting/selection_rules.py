"""比べる、勝負するレースの選び方の決まりの並び。"""

from __future__ import annotations

from .hardness_band import HARDNESS_BANDS
from .race_selection_rule import RaceSelectionRule

#: 今の買い方の、1開催日のレース数の候補（None は全部）。
_OPEN = (3, 5, 10, None)
#: 利用者が決めた「勝負レースは1日3レースまで」（買うレースと買い目を決める の決めごと 7）の中の候補。
_CAP3 = (1, 2, 3)

#: 今の買い方（2026-09-25 の研究の結果と同じ選び方）。
CURRENT_RULE = RaceSelectionRule("current", "今の買い方（上位 3・5・10・全部、消したレースを先に）", _OPEN, excluded_first=True)

#: 比べる選び方。上から、今の買い方 → 並べ方だけ変える → 堅さの帯を足す → 1日3レースまで → その両方 →
#: 重賞も3レースの枠に入れる。
SELECTION_RULES: tuple[RaceSelectionRule, ...] = (
    CURRENT_RULE,
    RaceSelectionRule("value_order", "今の買い方を期待値の順に並べる", _OPEN),
    RaceSelectionRule("hardness", "期待値の順＋堅さの帯", _OPEN, HARDNESS_BANDS),
    RaceSelectionRule("cap3", "1日3レースまで（重賞は別枠）", _CAP3),
    RaceSelectionRule("cap3_hardness", "1日3レースまで（重賞は別枠）＋堅さの帯", _CAP3, HARDNESS_BANDS),
    RaceSelectionRule("cap3_hardness_graded_in", "1日3レースまで（重賞も枠に入れる）＋堅さの帯", _CAP3, HARDNESS_BANDS,
                      graded_in_cap=True),
)


def rule_named(key: str) -> RaceSelectionRule:
    """保存の名前から選び方を引く。知らなければ ``ValueError``。"""
    for rule in SELECTION_RULES:
        if rule.key == key:
            return rule
    keys = " / ".join(rule.key for rule in SELECTION_RULES)
    raise ValueError(f"知らない選び方です: {key}（{keys}）")
