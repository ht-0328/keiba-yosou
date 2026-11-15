"""全レースの印の買い目の期待値（``MarkTicketValues``）と見込みの回収率（``MarkReturn``）のテスト。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 今週の予想.equal_payout_stakes import EqualPayoutStakes
from 今週の予想.mark_return import MarkReturn
from 今週の予想.mark_ticket_values import MarkTicketValues
from 今週の予想.mark_tickets import COLUMNS

TRIFECTA = "3連単（◎→○▲☆→○▲△☆）"


def test_単勝は馬の単勝の期待値_板と重みの無い券種は欠損値_ほかの行はそのまま() -> None:
    tickets = pd.DataFrame([
        {"race_id": "R1", "rule": "単勝", "ticket_type": "単勝", "combo": "03", "value": np.nan},
        {"race_id": "R1", "rule": "馬連", "ticket_type": "馬連", "combo": "0305", "value": np.nan},
        {"race_id": "R1", "rule": "3連単（◎軸・マルチ）", "ticket_type": "3連単", "combo": "030507", "value": 0.8},
    ]).reindex(columns=list(COLUMNS))
    marked = pd.DataFrame({"race_id": ["R1", "R1"], "horse_no": [3, 5], "win_value": [1.12, 0.7]})
    out = MarkTicketValues({}).attach(tickets, marked, {})
    assert out["value"].iloc[0] == pytest.approx(1.12)
    assert np.isnan(out["value"].iloc[1])
    assert out["value"].iloc[2] == pytest.approx(0.8)


def _ticket(rule: str, label: str, value: float | None, odds: float | None, dropped: str = "") -> dict:
    return {"rule": rule, "label": label, "value": value, "odds": odds, "dropped": dropped}


def test_どの組が当たっても同じ額が戻るように_オッズに反比例して配る() -> None:
    chosen, multiple = EqualPayoutStakes().allocate([_ticket("単勝", "3", 1.1, 4.0), _ticket("馬連", "3-5", 0.9, 10.0),
                                                     _ticket("馬単", "3→5", 1.3, 20.0)])
    assert [ticket["label"] for ticket, _ in chosen] == ["3→5", "3", "3-5"]   # 期待値の高い順
    assert [share for _, share in chosen] == pytest.approx([0.125, 0.625, 0.25])
    assert multiple == pytest.approx(2.5)
    for ticket, share in chosen:   # どれが当たっても、購入額 1 に対して 2.5 戻る
        assert share * ticket["odds"] == pytest.approx(2.5)


def test_払った額の1_1倍に届かなければ_期待値の低い組から外す() -> None:
    tickets = [_ticket("単勝", "3", 1.2, 1.5), _ticket("馬連", "3-5", 0.8, 3.0), _ticket("馬単", "3→5", 1.0, 6.0)]
    chosen, multiple = EqualPayoutStakes().allocate(tickets)   # 全部: Σ = 0.667 + 0.333 + 0.167 > 1
    assert [ticket["label"] for ticket, _ in chosen] == ["3", "3→5"] and multiple == pytest.approx(1 / (1 / 1.5 + 1 / 6.0))
    assert EqualPayoutStakes().allocate([_ticket("単勝", "3", 1.0, 1.05)]) == ([], None)


def test_見込みの回収率は_割合で重みを付けた期待値の和() -> None:
    forecast = {"timing": "当日", "tickets": [
        _ticket("単勝", "3", 1.2, 4.0), _ticket("馬連", "3-5", 0.9, 10.0), _ticket(TRIFECTA, "3→5→7", 1.5, 20.0),
        _ticket(TRIFECTA, "3→7→5", 9.9, 30.0, dropped="トリガミ"), _ticket("ワイド", "3-9", 3.0, 5.0)]}
    found = MarkReturn.of(forecast)
    assert found is not None and found.dropped == 0 and found.multiple == pytest.approx(2.5)
    assert found.expected == pytest.approx(0.625 * 1.2 + 0.25 * 0.9 + 0.125 * 1.5)
    assert list(found.stakes) == ["単勝", "馬連", TRIFECTA]
    # 1レース 5,000円を割合で分ける: 62.5% → 3,100円、25% → 1,300円、12.5% → 600円
    assert [yen for rows in found.stakes.values() for _, _, yen in rows] == [3100, 1300, 600]
    assert found.buys and found.total_yen == 5000 and found.least_return_yen == 12000   # 600円 × 20倍 = 12,000円がいちばん少ない
    assert found.heading() == "買う（見込みの回収率 116%）。合計 5,000円で、どれが当たっても 12,000円以上戻る"


def test_見込みの回収率が100パーセント未満なら見送り_100円に届かない組は100円() -> None:
    forecast = {"timing": "当日", "tickets": [_ticket("単勝", "3", 0.9, 2.0), _ticket(TRIFECTA, "3→5→7", 0.9, 500.0)]}
    found = MarkReturn.of(forecast)
    assert found is not None and not found.buys
    assert [yen for rows in found.stakes.values() for _, _, yen in rows] == [5000, 100]   # 3連単は 0.4% で 20円 → 100円
    assert found.heading().startswith("見送り（見込みの回収率 90%。100% 未満）。合計 5,100円")


def test_当日でないか買い目が無ければ出さない() -> None:
    assert MarkReturn.of({"timing": "前日", "tickets": [_ticket("単勝", "3", 1.2, 4.0)]}) is None
    assert MarkReturn.of({"timing": "当日", "tickets": [_ticket("ワイド", "3-9", 1.2, 4.0)]}) is None
