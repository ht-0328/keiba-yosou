"""印のルールの買い目（``MarkTickets``）・払戻とオッズ（``TicketPayouts``）・トリガミ（``TorigamiFilter``）・券種ごとの表（``TicketReport``）のテスト。

値は架空。DB は合成DB だけを使う。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from 印の成績.mark_tickets import MarkTickets
from 印の成績.ticket_payouts import ODDS, PAYOUT, TicketPayouts
from 印の成績.ticket_report import ALL_RACES, HIGH_RACES, TOTAL_LABEL, TicketReport
from 印の成績.torigami_filter import DROPPED, NO_ODDS, TORIGAMI, TorigamiFilter


def _marked_race(race_id: str = "R", expectation: str = "高") -> pd.DataFrame:
    """9頭のレース。◎3・○1・▲5・△2,4,6・☆8・注9・消7。複勝の期待値は 8番と 3番が線以上。"""
    marks = {3: "◎", 1: "○", 5: "▲", 2: "△", 4: "△", 6: "△", 8: "☆", 9: "注", 7: "消"}
    values = {3: 1.30, 8: 1.40, 1: 0.9, 5: 0.8, 2: 1.0, 4: 1.1, 6: 0.7, 9: 1.2, 7: 0.5}
    return pd.DataFrame({
        "race_id": race_id, "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半", "expectation": expectation,
        "horse_no": list(marks), "mark": list(marks.values()), "place_value": [values[no] for no in marks],
    })


def test_印のルールどおりに券種ごとの買い目を作る() -> None:
    tickets = MarkTickets().build(_marked_race())
    by_type = {label: sorted(group["combo"]) for label, group in tickets.groupby("ticket_type")}
    assert by_type["単勝"] == ["03"]
    assert by_type["ワイド"] == ["0308", "0309"]
    assert by_type["馬連"] == ["0103", "0305", "0308"]
    assert by_type["馬単"] == ["0301", "0305", "0308"]  # ◎ を1着に固定
    # 3連複: ◎ − ○▲☆ − ○▲△△△☆ で、同じ馬を含まない組（順不同）
    assert by_type["3連複"] == ["010203", "010304", "010305", "010306", "010308", "020305", "020308", "030405", "030408", "030506",
                                 "030508", "030608"]
    assert len(by_type["3連単"]) == 3 * 5  # ◎→(○▲☆)→残り5頭
    assert tickets[tickets["ticket_type"] == "複勝"]["combo"].tolist() == ["08", "03"]  # 期待値 1.25 以上を高い順
    assert set(tickets.columns) >= {"race_id", "race_date", "fold", "expectation", "ticket_type", "combo", "stake_units"}


def test_印の無い位置は飛ばし星も注も無ければワイドは作らない() -> None:
    race = _marked_race()
    race.loc[race["mark"].isin(["☆", "注"]), "mark"] = "消"
    tickets = MarkTickets().build(race)
    assert "ワイド" not in set(tickets["ticket_type"])
    assert sorted(tickets[tickets["ticket_type"] == "馬連"]["combo"]) == ["0103", "0305"]


def test_トリガミとオッズ無しの買い目を外す() -> None:
    tickets = pd.DataFrame({"race_id": "R", "ticket_type": "馬連", "combo": ["0103", "0305", "0308", "0309"],
                            ODDS: [2.5, 8.0, 30.0, np.nan]})
    filtered = TorigamiFilter().apply(tickets).set_index("combo")[DROPPED]
    # オッズ無しの 0309 を外すと3点。2.5倍は 3点の投資以下なので外す。残り2点（8.0・30.0）はどちらも投資より多く戻る
    assert filtered["0309"] == NO_ODDS and filtered["0103"] == TORIGAMI
    assert filtered["0305"] == "" and filtered["0308"] == ""


def test_合成DBから買い目の払戻とオッズを付ける(tmp_path: Path) -> None:
    from 共通 import keys
    from 合成DB import synth

    # 1レースに、3連単の払戻（4-2-3）と確定オッズ（4-2-3 は 1234.5倍、1-2-3 は無投票）を足した合成DB
    sample = synth.simple_race()
    ra = sample.ra[0]
    sample.headers.append(synth.payout_header(ra))
    sample.trifecta.append(synth.combo_payout(ra, "040203", 123450, table="hr__3連単払戻"))
    sample.odds.append(("o6", synth.odds_header(ra, "o6")))
    sample.odds.append(("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "040203", 12345)))
    sample.odds.append(("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "010203", 0, seq=2)))
    con = duckdb.connect(str(synth.build_db(tmp_path / "tickets.duckdb", sample)), read_only=True)
    race_id = "".join(ra[column] for column in keys.RACE_KEY)
    tickets = pd.DataFrame({"race_id": race_id, "race_date": pd.Timestamp("2024-04-06"), "fold": "x", "expectation": "高",
                            "ticket_type": "3連単", "combo": ["040203", "010203", "050403"], "stake_units": 0.1})
    attached = TicketPayouts(con).attach(tickets).set_index("combo")
    assert attached.loc["040203", PAYOUT] == pytest.approx(123450.0) and attached.loc["040203", ODDS] == pytest.approx(1234.5)
    assert attached.loc["010203", PAYOUT] == 0.0 and np.isnan(attached.loc["010203", ODDS])  # 無投票の組はオッズ無し
    assert attached.loc["050403", PAYOUT] == 0.0 and np.isnan(attached.loc["050403", ODDS])  # 表に無い組


def test_券種ごとの表は全レースと期待度が高の2つの対象で出す() -> None:
    tickets = pd.concat([MarkTickets().build(_marked_race("A", "高")), MarkTickets().build(_marked_race("B", "低"))], ignore_index=True)
    tickets[ODDS] = 5.0
    tickets[PAYOUT] = np.where((tickets["ticket_type"] == "単勝") & (tickets["race_id"] == "A"), 500.0, 0.0)
    tickets[DROPPED] = ""
    tables = TicketReport().tables(tickets, races=2, days=1)
    assert [table.title[:2] for table in tables] == ["7.", "8."]
    rows = {(row[0], row[1]): row for row in tables[0].rows}
    assert rows[("単勝", ALL_RACES)][2:8] == ["2", "2", "1.0", "200円", "500円", "250.0%"]
    assert rows[("単勝", HIGH_RACES)][2:8] == ["1", "1", "1.0", "100円", "500円", "500.0%"]
    assert rows[("馬単（設計書に無い）", ALL_RACES)][3] == "6"
    assert (TOTAL_LABEL, ALL_RACES) in rows and (TOTAL_LABEL, HIGH_RACES) in rows
    csv = TicketReport().csv_frame(tickets)
    assert list(csv.columns)[:4] == ["レースID", "開催日", "区切り", "期待度"] and len(csv) == len(tickets)


def test_券種の名前は払戻の表と対応する() -> None:
    assert TicketType.parse("3連複").spec.payout_table == "hr__3連複払戻"
