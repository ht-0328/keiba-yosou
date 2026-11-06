"""TicketPlan（券種ごとの買い方）の、名前・点数の上限・荒れ具合の条件のテスト。架空の値。"""

from __future__ import annotations

import pandas as pd
import pytest

from 地方の推奨買目.position_model import EV, PROBABILITY
from 地方の推奨買目.ticket_plan import RECOMMENDED_PLANS, TicketPlan


def test_買い方の名前は_帯_線_形_荒れ具合_点数の上限を並べる():
    plan = TicketPlan("3連複", 1.0, 10.0, 100.0, min_heads=8, top_k=3, upset_min=0.6)
    assert plan.label == "10〜100倍・期待値 1 以上・中荒れ以上の確率 0.6 以上・期待値の上位 3 点"
    assert TicketPlan("馬連", 1.0, 0.0, 20.0, form="人中").label == "〜20倍・期待値 1 以上・型 人中"


def test_点数の上限は_期待値の高い順に残す():
    table = pd.DataFrame({"race_id": [1] * 4, "a": [1, 1, 2, 3], "b": [2, 3, 3, 4], "c": [3, 4, 4, 5],
                          PROBABILITY: [0.02, 0.03, 0.01, 0.05], "odds": [60.0, 40.0, 90.0, 15.0]})
    chosen = TicketPlan("3連複", 0.5, 10.0, 100.0, top_k=2).choose(table)
    # 期待値は 1.2・1.2・0.9・0.75。上位2点は 1-2-3 と 1-3-4（同じ期待値なら元の順）
    assert [(int(row.a), int(row.b), int(row.c)) for row in chosen.itertuples()] == [(1, 2, 3), (1, 3, 4)]
    assert chosen[EV].tolist() == pytest.approx([1.2, 1.2])


def test_荒れ具合の条件は_線以上のレースだけで_値が無ければ買わない():
    plan = TicketPlan("3連複", 1.0, 10.0, 100.0, upset_min=0.6)
    assert plan.allows_upset(0.6) and not plan.allows_upset(0.59) and not plan.allows_upset(None)
    assert TicketPlan("単勝", 1.0, 0.0, 30.0).allows_upset(None)


def test_本番の買い方は_3連複だけ荒れ具合の条件と点数の上限つき():
    by_ticket = {plan.ticket: plan for plan in RECOMMENDED_PLANS}
    assert by_ticket["3連複"] == TicketPlan("3連複", 1.0, 10.0, 100.0, min_heads=8, top_k=3, upset_min=0.6)
    assert all(plan.upset_min == 0 and plan.top_k == 0 for ticket, plan in by_ticket.items() if ticket != "3連複")
    assert list(by_ticket) == ["単勝", "複勝", "枠連", "馬連", "ワイド", "馬単", "3連複", "3連単"]
