"""払戻とオッズ（``TicketPayouts``）・買い方ごとの表（``TicketReport``・``LineSensitivityReport``）のテスト。

値は架空。DB は合成DB だけを使う。買い目は今週の予想の ``MarkTickets`` で作る（そのテストは ``今週の予想/tests/test_weekly_tickets.py``）。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from 今週の予想.mark_tickets import ODDS, RULE, VALUE, MarkTickets
from 今週の予想.tests.test_weekly_tickets import _marked_race
from 今週の予想.torigami_filter import DROPPED

from 印の成績.line_sensitivity_report import LineSensitivityReport
from 印の成績.ticket_payouts import PAYOUT, TicketPayouts
from 印の成績.ticket_report import ALL_RACES, HIGH_RACES, TicketReport, total_label


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
                            RULE: ["A", "A", "A", "B"], "ticket_type": "3連単", "combo": ["040203", "010203", "050403", "040203"],
                            "stake_units": 0.1})
    attached = TicketPayouts(con).attach(tickets)
    first = attached[attached[RULE] == "A"].set_index("combo")
    assert first.loc["040203", PAYOUT] == pytest.approx(123450.0) and first.loc["040203", ODDS] == pytest.approx(1234.5)
    assert first.loc["010203", PAYOUT] == 0.0 and np.isnan(first.loc["010203", ODDS])  # 無投票の組はオッズ無し
    assert first.loc["050403", PAYOUT] == 0.0 and np.isnan(first.loc["050403", ODDS])  # 表に無い組
    assert attached[attached[RULE] == "B"][PAYOUT].iloc[0] == pytest.approx(123450.0)  # 別の買い方の同じ組にも付く


def test_買い方ごとの表は全レースと期待度が高の2つの対象で出し合計は軸のパターンごと() -> None:
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
    # 合計（元の買い目だけ）: 単勝1 + 複勝2 + ワイド2 + 馬連3 + 馬単3 + 元の3連複12 + 元の3連単15
    base = 1 + 2 + 2 + 3 + 3 + 12 + 15
    assert rows[(total_label("元の買い目だけ"), HIGH_RACES)][3] == f"{base}"
    assert rows[("3連単（◎軸・マルチ）", ALL_RACES)][3] == "180" and rows[("3連複（軸馬・流し）", HIGH_RACES)][3] == "15"
    # 合計（◎軸）は、元の買い目は必ず入れ、3連複（◎軸・流し）15 と 3連単（◎軸・マルチ・期待値）の点数を足したもの
    priced = int((tickets[RULE] == "3連単（◎軸・マルチ・期待値 1.0 以上）").sum() / 2)
    assert rows[(total_label("◎軸"), HIGH_RACES)][3] == f"{base + 15 + priced}"
    assert (total_label("軸馬"), ALL_RACES) in rows
    assert [row[0] for row in tables[1].rows[:2]] == ["単勝", "複勝"]
    csv = TicketReport().csv_frame(tickets)
    assert list(csv.columns)[:6] == ["レースID", "開催日", "区切り", "期待度", "買い方", "券種"] and len(csv) == len(tickets)
    assert csv["組の確率"].notna().sum() == tickets[VALUE].notna().sum()  # 組の確率 = 期待値 ÷ オッズ（3連複・3連単だけ）


def test_線を動かした表は全点の買い目を線で絞って出す() -> None:
    tickets = MarkTickets().build(_marked_race("A", "高"))
    tickets[ODDS] = 5.0
    tickets[PAYOUT] = 0.0
    tickets[DROPPED] = ""
    table = LineSensitivityReport().table(tickets)
    assert table.title.startswith("9.")
    rows = {(row[0], row[1], row[2]): row for row in table.rows}
    full = tickets[tickets[RULE] == "3連単（◎軸・マルチ）"]
    assert rows[("3連単（◎軸・マルチ）", ALL_RACES, "1.0")][4] == f"{int((full[VALUE] >= 1.0).sum())}"
    assert rows[("3連単（◎軸・マルチ）", HIGH_RACES, "2.0")][4] == f"{int((full[VALUE] >= 2.0).sum())}"
    assert ("3連複（軸馬・流し）", ALL_RACES, "1.5") in rows and not any(label.endswith("以上）") for label, _, _ in rows)


def test_券種の名前は払戻の表と対応する() -> None:
    assert TicketType.parse("3連複").spec.payout_table == "hr__3連複払戻"
