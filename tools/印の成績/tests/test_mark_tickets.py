"""印のルールの買い目（``MarkTickets``）・払戻とオッズ（``TicketPayouts``）・トリガミ（``TorigamiFilter``）・買い方ごとの表（``TicketReport``・
``LineSensitivityReport``）のテスト。

値は架空。DB は合成DB だけを使う。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from 印の成績.line_sensitivity_report import LineSensitivityReport
from 印の成績.mark_tickets import RULE, VALUE, MarkTickets
from 印の成績.ticket_payouts import ODDS, PAYOUT, TicketPayouts
from 印の成績.race_filters import ALL_RACES, HIGH_RACES, TARGETS
from 印の成績.ticket_report import TicketReport, total_label
from 印の成績.ticket_rules import RULE_LABELS
from 印の成績.torigami_filter import DROPPED, NO_ODDS, TORIGAMI, TorigamiFilter

#: 9頭のレースの印。◎3・○1・▲5・△2,4,6・☆8・注9・消7。軸馬は ○ の 1番（3着以内の確率が ◎ より高い）。
_MARKS = {3: "◎", 1: "○", 5: "▲", 2: "△", 4: "△", 6: "△", 8: "☆", 9: "注", 7: "消"}
#: 馬ごとの「モデル ÷ 市場」の比（3着以内の比・1着の比）。市場の見立ては 3着以内 0.5・1着 0.1 でそろえる。
_TOP3_RATIO = {3: 1.2, 1: 1.1, 5: 1.0, 2: 0.9, 4: 1.0, 6: 0.8, 8: 1.5, 9: 1.0, 7: 0.7}
_WIN_RATIO = {3: 1.5, 1: 1.0, 5: 1.0, 2: 1.0, 4: 1.0, 6: 1.0, 8: 1.2, 9: 1.0, 7: 1.0}


def _marked_race(race_id: str = "R", expectation: str = "高") -> pd.DataFrame:
    """複勝の期待値は 8番と 3番が線以上。並びは3着以内の確率の高い順（軸馬の 1番が先頭）。"""
    values = {3: 1.30, 8: 1.40, 1: 0.9, 5: 0.8, 2: 1.0, 4: 1.1, 6: 0.7, 9: 1.2, 7: 0.5}
    order = sorted(_MARKS, key=lambda no: -_TOP3_RATIO[no])
    return pd.DataFrame({
        "race_id": race_id, "race_date": pd.Timestamp("2025-01-05"), "fold": "2025年前半", "expectation": expectation,
        "horse_no": order, "mark": [_MARKS[no] for no in order], "place_value": [values[no] for no in order],
        "probability": [0.5 * _TOP3_RATIO[no] for no in order], "market_top3": 0.5,
        "win_probability": [0.1 * _WIN_RATIO[no] for no in order], "market_win": 0.1,
        "axis": [no == 1 for no in order],
    })


def _by_rule(tickets: pd.DataFrame) -> dict[str, list[str]]:
    return {label: sorted(group["combo"]) for label, group in tickets.groupby(RULE)}


def test_印の位置で組む券種と複勝の買い目() -> None:
    by_rule = _by_rule(MarkTickets().build(_marked_race()))
    assert by_rule["単勝"] == ["03"]
    assert by_rule["ワイド"] == ["0308", "0309"]
    assert by_rule["馬連"] == ["0103", "0305", "0308"]
    assert by_rule["馬単（設計書に無い）"] == ["0301", "0305", "0308"]  # ◎ を1着に固定
    assert by_rule["複勝"] == ["03", "08"]  # 期待値 1.25 以上（高い順は 8 → 3）
    # 元の3連複: ◎ − ○▲☆ − ○▲△△△☆ で、同じ馬を含まない組（順不同）。元の3連単: ◎→(○▲☆)→残り5頭
    assert by_rule["3連複（◎−○▲☆−○▲△☆）"] == ["010203", "010304", "010305", "010306", "010308", "020305", "020308", "030405", "030408",
                                             "030506", "030508", "030608"]
    assert len(by_rule["3連単（◎→○▲☆→○▲△☆）"]) == 3 * 5
    # モデルごとの確率の無い表では、2モデル一致の行は出ない
    assert set(by_rule) == {label for label in RULE_LABELS if "2モデル一致" not in label}


def test_3連複は軸の1頭から相手6頭に流して15点で軸馬のときは二重丸が相手に回る() -> None:
    by_rule = _by_rule(MarkTickets().build(_marked_race()))
    top = by_rule["3連複（◎軸・流し）"]
    assert len(top) == 15 and all("03" in {combo[0:2], combo[2:4], combo[4:6]} for combo in top)
    assert "010308" in top and "020406" not in top and all("09" not in (c[0:2], c[2:4], c[4:6]) for c in top)  # 注は相手にしない
    horse = by_rule["3連複（軸馬・流し）"]
    assert len(horse) == 15 and all(combo[0:2] == "01" for combo in horse) and "010305" in horse  # 軸は 1番で、◎ の 3番は相手


def test_3連単は軸の1頭からのマルチで90点になり期待値が線以上の買い目だけ残す() -> None:
    tickets = MarkTickets().build(_marked_race())
    full = tickets[tickets[RULE] == "3連単（◎軸・マルチ）"].set_index("combo")
    assert len(full) == 90 and all("03" in (c[0:2], c[2:4], c[4:6]) for c in full.index)
    # 期待値 = 0.725 × 1着の比 × 2着・3着の3着以内の比。3→1→8 は 0.725 × 1.5 × 1.1 × 1.5
    assert full.loc["030108", VALUE] == pytest.approx(0.725 * 1.5 * 1.1 * 1.5)
    assert full.loc["010308", VALUE] == pytest.approx(0.725 * 1.0 * 1.2 * 1.5)  # 1着が 1番なら 1番の1着の比
    assert full.loc["060302", VALUE] == pytest.approx(0.725 * 1.0 * 1.2 * 0.9)
    priced = tickets[tickets[RULE] == "3連単（◎軸・マルチ・期待値 1.0 以上）"].set_index("combo")
    assert (priced[VALUE] >= 1.0).all() and len(priced) == int((full[VALUE] >= 1.0).sum())
    assert "030108" in priced.index and "060302" not in priced.index
    # 3連複の期待値は 3頭とも3着以内の比（0.75 × 1.2 × 1.1 × 1.5）。線以上は 8番を含む 5点
    trio = tickets[tickets[RULE] == "3連複（◎軸・流し）"].set_index("combo")
    assert trio.loc["010308", VALUE] == pytest.approx(0.75 * 1.2 * 1.1 * 1.5)
    assert sorted(tickets[tickets[RULE] == "3連複（◎軸・流し・期待値 1.0 以上）"]["combo"]) == ["010308", "020308", "030408", "030508", "030608"]
    assert tickets[tickets["ticket_type"].isin(["単勝", "複勝", "ワイド", "馬連", "馬単"])][VALUE].isna().all()


def test_軸の列が無ければ軸馬も二重丸で市場の見立てが無ければ期待値は付かない() -> None:
    race = _marked_race().drop(columns=["axis", "market_top3", "market_win"])
    by_rule = _by_rule(MarkTickets().build(race))
    assert by_rule["3連複（軸馬・流し）"] == by_rule["3連複（◎軸・流し）"]
    assert "3連単（◎軸・マルチ・期待値 1.0 以上）" not in by_rule and len(by_rule["3連単（◎軸・マルチ）"]) == 90


def test_印の無い位置は飛ばし星も注も無ければワイドは作らない() -> None:
    race = _marked_race()
    race.loc[race["mark"].isin(["☆", "注"]), "mark"] = "消"
    by_rule = _by_rule(MarkTickets().build(race))
    assert "ワイド" not in by_rule
    assert by_rule["馬連"] == ["0103", "0305"]
    assert len(by_rule["3連複（◎軸・流し）"]) == 10  # 相手は ○▲△△△ の5頭


def test_トリガミとオッズ無しの買い目を外す() -> None:
    tickets = pd.DataFrame({"race_id": "R", RULE: "馬連", "ticket_type": "馬連", "combo": ["0103", "0305", "0308", "0309"],
                            ODDS: [2.5, 8.0, 30.0, np.nan]})
    filtered = TorigamiFilter().apply(tickets).set_index("combo")[DROPPED]
    # オッズ無しの 0309 を外すと3点。2.5倍は 3点の投資以下なので外す。残り2点（8.0・30.0）はどちらも投資より多く戻る
    assert filtered["0309"] == NO_ODDS and filtered["0103"] == TORIGAMI
    assert filtered["0305"] == "" and filtered["0308"] == ""


def test_トリガミは買い方ごとに見る() -> None:
    # 同じ券種でも買い方が違えば別に数える: 全点（3点）では 2.5倍はトリガミ、期待値で絞った1点では残る
    tickets = pd.DataFrame({"race_id": "R", RULE: ["A", "A", "A", "B"], "ticket_type": "3連複",
                            "combo": ["010203", "010204", "010205", "010203"], ODDS: [2.5, 8.0, 30.0, 2.5]})
    filtered = TorigamiFilter().apply(tickets)
    assert filtered[DROPPED].tolist() == [TORIGAMI, "", "", ""]


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


def test_買い方ごとの表は絞り込みごとに出し合計は軸のパターンごと() -> None:
    tickets = pd.concat([MarkTickets().build(_marked_race("A", "高")), MarkTickets().build(_marked_race("B", "低"))], ignore_index=True)
    tickets[ODDS] = 5.0
    tickets[PAYOUT] = np.where((tickets["ticket_type"] == "単勝") & (tickets["race_id"] == "A"), 500.0, 0.0)
    tickets[DROPPED] = ""
    tables = TicketReport().tables(tickets, races=2, days=1)
    assert [table.title[:2] for table in tables] == ["7.", "8."]
    rows = {(row[0], row[1]): row for row in tables[0].rows}
    assert rows[("単勝", ALL_RACES.label)][2:8] == ["2", "2", "1.0", "200円", "500円", "250.0%"]
    assert rows[("単勝", HIGH_RACES.label)][2:8] == ["1", "1", "1.0", "100円", "500円", "500.0%"]
    assert rows[("馬単（設計書に無い）", ALL_RACES.label)][3] == "6"
    # 合計（元の買い目だけ）: 単勝1 + 複勝2 + ワイド2 + 馬連3 + 馬単3 + 元の3連複12 + 元の3連単15
    base = 1 + 2 + 2 + 3 + 3 + 12 + 15
    assert rows[(total_label("元の買い目だけ"), HIGH_RACES.label)][3] == f"{base}"
    assert rows[("3連単（◎軸・マルチ）", ALL_RACES.label)][3] == "180" and rows[("3連複（軸馬・流し）", HIGH_RACES.label)][3] == "15"
    # 合計（◎軸）は、元の買い目は必ず入れ、3連複（◎軸・流し）15 と 3連単（◎軸・マルチ・期待値）の点数を足したもの
    priced = int((tickets[RULE] == "3連単（◎軸・マルチ・期待値 1.0 以上）").sum() / 2)
    assert rows[(total_label("◎軸"), HIGH_RACES.label)][3] == f"{base + 15 + priced}"
    assert (total_label("軸馬"), ALL_RACES.label) in rows
    assert [row[0] for row in tables[1].rows[:3]] == ["単勝", "複勝", "複勝（2モデル一致）"]
    assert {row[1] for row in tables[0].rows} == {target.label for target in TARGETS}
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
    assert rows[("3連単（◎軸・マルチ）", ALL_RACES.label, "1.0")][4] == f"{int((full[VALUE] >= 1.0).sum())}"
    assert rows[("3連単（◎軸・マルチ）", HIGH_RACES.label, "2.0")][4] == f"{int((full[VALUE] >= 2.0).sum())}"
    assert ("3連複（軸馬・流し）", ALL_RACES.label, "1.5") in rows and not any(label.endswith("以上）") for label, _, _ in rows)


def test_券種の名前は払戻の表と対応する() -> None:
    assert TicketType.parse("3連複").spec.payout_table == "hr__3連複払戻"
