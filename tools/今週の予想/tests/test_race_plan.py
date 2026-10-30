"""RacePlan（1レースの買う計画）の書き出しと読み戻しのテスト。値は架空。"""

from __future__ import annotations

from yosou.review import names

from 今週の予想.race_plan import PlacePick, RacePlan
from 今週の予想.ticket_pick import TicketPick


def test_計画は書いて読み戻すと同じで_種類の無い前の版の買い目は勝負の単勝馬単になる() -> None:
    plan = RacePlan("2025041905010101", "2025-04-19（土） 東京 1R", "当日", "勝負", "見込みの利益 E = 0.30単位 > 0", 0.3, 1.05, False,
                    (PlacePick(3, 0.42, 1.05, 1.5, 1600),), 5000,
                    (TicketPick("単勝", "03", "3", 1.085, 3.1, 300), TicketPick("ワイド", "0103", "1-3", 1.2, 6.0, 100, kind=names.MATCH_COMBO)),
                    "◎の単勝の期待値が 1.00 以上")
    data = plan.to_dict()
    assert data["stake_yen"] == 2000 and data["tickets"][1]["kind"] == names.MATCH_COMBO
    assert RacePlan.from_dict(data) == plan

    # 組の期待値を買う前の版の plan.json（買い目に kind が無い）
    old = {key: value for key, value in data.items() if key not in ("stake_yen", "place_yen", "ticket_yen")}
    old["tickets"] = [{key: value for key, value in ticket.items() if key != "kind"} for ticket in data["tickets"]]
    restored = RacePlan.from_dict(old)
    assert all(ticket.kind == names.MATCH_WIN for ticket in restored.tickets) and restored.stake_yen == 2000 and restored.buys


def test_買い目の無い計画も読み戻せる() -> None:
    plan = RacePlan("2025041905010102", "2025-04-19（土） 東京 2R", "前日", "買わない", "期待値が線に届かない", 0.0, None, False)
    assert RacePlan.from_dict(plan.to_dict()) == plan and not RacePlan.from_dict(plan.to_dict()).buys
