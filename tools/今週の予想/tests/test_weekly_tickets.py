"""印のルールの買い目（``MarkTickets``）・トリガミ（``TorigamiFilter``）・今週の予想の買い目（``ForecastTickets``）のテスト。

値は架空。DB は合成DB だけを使う。
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from 今週の予想.forecast_tickets import TICKET_KEYS, ForecastTickets
from 今週の予想.mark_tickets import ODDS, RULE, VALUE, MarkTickets
from 今週の予想.ticket_rules import RULE_LABELS
from 今週の予想.torigami_filter import DROPPED, NO_ODDS, TORIGAMI, TorigamiFilter

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
    assert set(by_rule) == set(RULE_LABELS)


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


def test_今週の予想の買い目は締め切り前のオッズで期待値とトリガミを付ける(tmp_path: Path) -> None:
    from 共通 import keys
    from 合成DB import synth

    # 締め切り前の断面（データ区分 1）: 単勝 3番 5.0倍、複勝 3番 1.8〜2.4倍・8番 4.0〜6.0倍、3連単 3→1→8 が 60.0倍、
    # 3連複 1-3-8 が 1.5倍・1-3-5 が 30.0倍（オッズ無しの組を外すと2点なので、1.5倍はトリガミになる）
    sample = synth.simple_race()
    ra = sample.ra[0]
    at = "04061200"
    sample.odds.append(("o1", synth.odds_header(ra, "o1", stage="1", announced=at)))
    sample.odds.append(("o1__単勝オッズ", synth.odds_row(ra, "o1__単勝オッズ", "03", 50, announced=at)))
    sample.odds.append(("o1__複勝オッズ", synth.range_odds_row(ra, "o1__複勝オッズ", "03", 18, 24, announced=at)))
    sample.odds.append(("o1__複勝オッズ", synth.range_odds_row(ra, "o1__複勝オッズ", "08", 40, 60, seq=2, announced=at)))
    sample.odds.append(("o6", synth.odds_header(ra, "o6", stage="1", announced=at)))
    sample.odds.append(("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "030108", 600, announced=at)))
    sample.odds.append(("o5", synth.odds_header(ra, "o5", stage="1", announced=at)))
    sample.odds.append(("o5__3連複オッズ", synth.odds_row(ra, "o5__3連複オッズ", "010308", 15, announced=at)))
    sample.odds.append(("o5__3連複オッズ", synth.odds_row(ra, "o5__3連複オッズ", "010305", 300, seq=2, announced=at)))
    con = duckdb.connect(str(synth.build_db(tmp_path / "weekly.duckdb", sample)), read_only=True)
    race_id = "".join(ra[column] for column in keys.RACE_KEY)

    tickets = ForecastTickets().build(con, race_id, _marked_race(), "高", odds_known=True)
    assert tickets and all(tuple(ticket) == TICKET_KEYS for ticket in tickets)
    by_key = {(ticket["rule"], ticket["combo"]): ticket for ticket in tickets}
    win = by_key[("単勝", "03")]
    assert win["odds"] == 5.0 and win["label"] == "3" and win["horses"] == [3] and win["dropped"] == "" and win["value"] is None
    assert by_key[("複勝", "08")]["odds"] == 4.0 and by_key[("複勝", "03")]["odds"] == 1.8
    trifecta = by_key[("3連単（◎軸・マルチ・期待値 1.0 以上）", "030108")]
    assert trifecta["label"] == "3→1→8" and trifecta["odds"] == 60.0
    assert trifecta["value"] == pytest.approx(0.725 * 1.5 * 1.1 * 1.5) and trifecta["probability"] == pytest.approx(trifecta["value"] / 60.0)
    # オッズの無い組は「オッズ無し」、3連複の 1-3-8 は 1.5倍で 15点の投資より少ないのでトリガミ
    assert by_key[("3連単（◎軸・マルチ・期待値 1.0 以上）", "030801")]["dropped"] == "オッズ無し"
    trio = {combo: by_key[("3連複（◎軸・流し）", combo)] for combo in ("010308", "010305", "020308")}
    assert trio["010308"]["label"] == "1-3-8" and trio["010308"]["dropped"] == "トリガミ"
    assert trio["010305"]["dropped"] == "" and trio["020308"]["dropped"] == "オッズ無し"
    # オッズの無い時点（木曜）は、組むだけでオッズ・期待値・トリガミは付かない
    thursday = ForecastTickets().build(con, race_id, _marked_race().drop(columns=["market_top3", "market_win"]), None, odds_known=False)
    assert thursday and all(ticket["odds"] is None and ticket["dropped"] == "" and ticket["value"] is None for ticket in thursday)
    assert not any(ticket["rule"].endswith("以上）") for ticket in thursday)
