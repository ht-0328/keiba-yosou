"""その日の結果（1レースの精算 ``RaceResult``・着順 ``DayFinishes``・表 ``DayTables``）のテスト。値は架空。"""

from __future__ import annotations

from datetime import date

import duckdb

from その日の結果.day_finishes import DayFinishes
from その日の結果.day_tables import HIGH_PAYOUT_TOTAL, WAITING, DayTables
from その日の結果.race_result import RaceResult

from 今週の予想.ticket_rules import HIGH_PAYOUT_TICKET_TYPES

RID = "2026112805050101"
#: 10頭。逃げ・先行は 1・2 の2頭（20%）。
SLOW = {1: "逃げ", 2: "先行", **{number: "差し" for number in range(3, 11)}}


class _Payouts:
    """単勝 5 が 400円、馬連 5-7 が 1,000円、枠連 5-7 が 600円。``known`` が偽なら払戻が届いていない。"""

    def __init__(self, known: bool = True) -> None:
        self._known = known
        self._yen = {("単勝", "05"): 400, ("馬連", "0507"): 1000, ("枠連", "57"): 600}

    def has(self, race_id: str) -> bool:
        return self._known

    def yen(self, race_id: str, ticket_type: str, combo: str) -> int | None:
        return None if ticket_type == "謎" else self._yen.get((ticket_type, combo), 0)


def _forecast(win_value: float = 1.2) -> dict:
    marks = {5: "◎", 7: "○", 3: "▲"}
    horses = [{"horse_no": number, "mark": marks.get(number, "－")} for number in range(1, 11)]
    tickets = [{"rule": "単勝", "ticket_type": "単勝", "combo": "05", "label": "5", "value": win_value, "odds": 4.0, "dropped": ""}]
    plan = {"picks": [{"horse_no": 5, "probability": 0.5, "value": 1.3, "odds": 1.5, "yen": 1000}],
            "tickets": [{"ticket_type": "馬連", "combo": "0507", "label": "5-7", "value": 1.1, "odds": 10.0, "yen": 300, "kind": "勝負"},
                        {"ticket_type": "枠連", "combo": "57", "label": "5-7", "value": 1.1, "odds": 6.0, "yen": 200, "kind": "勝負"},
                        {"ticket_type": "謎", "combo": "01", "label": "1", "value": 1.0, "odds": 2.0, "yen": 100, "kind": "勝負"}]}
    return {"rid": RID, "timing": "当日", "header": {"競馬場": "東京", "R": 1}, "horses": horses, "tickets": tickets, "plan": plan}


FINISHES = [(1, 5), (2, 7), (3, 9)]


def test_着順と印_実際に買う買い目と印の買い目を払戻で精算する() -> None:
    result = RaceResult(_forecast(), FINISHES, _Payouts(), {})
    assert result.finished and result.marks_line() == "◎5 ○7 ▲3"
    assert result.top3() == "1着 5◎・2着 7○・3着 9－" and result.top_finish() == "1着"
    # 複勝 5 は払戻の表に無いので 0、馬連 300円 × 10倍、枠連 200円 × 6倍。知らない券種の 100円は払戻を読めない
    plan = result.plan()
    assert (plan.stake, plan.back, plan.unknown) == (1600, 3000 + 1200, 100)
    # 印の買い目は単勝 5 に 5,000円（見込みの回収率 120% で買う）
    assert (result.marks().stake, result.marks().back) == (5000, 20000)
    assert RaceResult(_forecast(), [(1, 2)], _Payouts(), {}).top_finish() == "着外"


def test_AIが見送るレースは数えず_ロジックで見送ったレースはAIとロジックだけ買わない() -> None:
    assert RaceResult(_forecast(win_value=0.8), FINISHES, _Payouts(), {}).marks().stake == 0
    skipped = RaceResult(_forecast(), FINISHES, _Payouts(), SLOW)   # ◎ の 5 は差しで、逃げ・先行は 20%
    assert skipped.marks().stake == 5000 and skipped.logic().stake == 0 and skipped.logic_skip() == "展開"
    assert RaceResult(_forecast(), FINISHES, _Payouts(), {}).logic_skip() == ""


def test_表は結果の届いたレースだけを合計し_届いていないレースは結果待ち() -> None:
    done, waiting = RaceResult(_forecast(), FINISHES, _Payouts(), SLOW), RaceResult(_forecast(), [], _Payouts(known=False), {})
    races, totals = DayTables().build(date(2026, 11, 28), [(_forecast(), done), (_forecast(), waiting)])
    # 最後の列は高配当の買い目。この予想には入っていないので「買わない」
    assert races.rows[0][3:] == ["1着 5◎・2着 7○・3着 9－", "1着", "1,600円 → 4,200円（うち 100円は払戻を読めない券種）", "5,000円 → 20,000円", "見送り（展開）",
                                 "買わない"]
    assert races.rows[1][3] == WAITING and len(races.rows[1]) == len(races.columns)
    assert totals.rows[:3] == [["実際に買う買い目", 1, 1, "1,600円", "4,200円", "262.5%", "+2,600円"],
                               ["印の買い目（AI だけ）", 1, 1, "5,000円", "20,000円", "400.0%", "+15,000円"],
                               ["印の買い目（AI＋ロジック）", 0, 0, "0円", "0円", "-", "+0円"]]
    # 高配当の買い目の行は、今の対象の券種ごとと合計。どのレースも買っていないので 0
    assert [row[0] for row in totals.rows[3:]] == [f"高配当の買い目（{ticket_type.label}）" for ticket_type in HIGH_PAYOUT_TICKET_TYPES] + [HIGH_PAYOUT_TOTAL]
    assert all(row[1:] == [0, 0, "0円", "0円", "-", "+0円"] for row in totals.rows[3:])
    assert "結果の届いたレース 1／予想のあるレース 2" in totals.note


def _with_high_payout() -> dict:
    """高配当の買い目が、馬連 5-7・3-5 とワイド 5-9・外した 3連単 1点の予想（当日。決まりは期待値 1.05 以上）。"""
    forecast = _forecast()
    forecast["high_payout"] = {"ready": True, "value_line": 1.05, "max_points": None, "high_lines": {"ワイド": 10.0, "馬連": 30.0}}
    forecast["tickets"] += [
        {"rule": "馬連（高配当）", "ticket_type": "馬連", "combo": "0507", "label": "5-7", "value": 1.2, "odds": 40.0, "dropped": ""},
        {"rule": "馬連（高配当）", "ticket_type": "馬連", "combo": "0305", "label": "3-5", "value": 1.1, "odds": 55.0, "dropped": ""},
        {"rule": "ワイド（高配当）", "ticket_type": "ワイド", "combo": "0509", "label": "5-9", "value": 1.3, "odds": 12.0, "dropped": ""},
        {"rule": "3連単（高配当）", "ticket_type": "3連単", "combo": "050709", "label": "5→7→9", "value": 1.4, "odds": None, "dropped": "オッズ無し"},
    ]
    return forecast


def test_高配当の買い目は1点100円で精算し_レースごとの列と券種ごとの行と合計の行に出す() -> None:
    result = RaceResult(_with_high_payout(), FINISHES, _Payouts(), {})
    # 馬連 2点（5-7 は 1,000円の払戻）・ワイド 1点（外れ）。外した 3連単は買わない
    assert (result.high_payout().stake, result.high_payout().back) == (300, 1000)
    assert (result.high_payout_of("馬連").stake, result.high_payout_of("馬連").back) == (200, 1000)
    assert (result.high_payout_of("ワイド").stake, result.high_payout_of("ワイド").back) == (100, 0)
    assert result.high_payout_of("3連単").stake == 0
    # 印の買い目（単勝 ◎）の精算は、高配当の買い目を足しても変わらない
    assert (result.marks().stake, result.marks().back) == (5000, 20000)
    plain = RaceResult(_forecast(), FINISHES, _Payouts(), {})
    races, totals = DayTables().build(date(2026, 11, 28), [(_with_high_payout(), result), (_forecast(), plain)])
    assert races.columns[-1] == "高配当の買い目"
    assert [row[-1] for row in races.rows] == ["300円 → 1,000円", "買わない"]
    by_name = {row[0]: row[1:] for row in totals.rows}
    assert by_name["高配当の買い目（馬連）"] == [1, 1, "200円", "1,000円", "500.0%", "+800円"]
    assert by_name["高配当の買い目（ワイド）"] == [1, 0, "100円", "0円", "0.0%", "-100円"]
    assert by_name["高配当の買い目（3連複）"] == [0, 0, "0円", "0円", "-", "+0円"]
    assert "高配当の買い目（3連単）" not in by_name   # 対象でない券種は、その日に買った点が無ければ行を出さない
    assert by_name[HIGH_PAYOUT_TOTAL] == [1, 1, "300円", "1,000円", "333.3%", "+700円"]
    assert "高配当の買い目は 1点 100円" in totals.note


def _with_danger(number: int, win_probability: float) -> dict:
    """``number`` の馬を消にした予想（市場の見立ては 0.25）。"""
    forecast = _forecast()
    forecast["horses"][number - 1] = {"horse_no": number, "mark": "消", "is_danger": True, "win_probability": win_probability, "market_win": 0.25}
    return forecast


def test_消が1着になったかは_AIだけと_取り消した消を除いたAIとロジックで数える() -> None:
    won = [(1, 2), (2, 5), (3, 7)]
    kept, cancelled = _with_danger(2, 0.20), _with_danger(2, 0.30)
    assert RaceResult(kept, won, _Payouts(), {}).danger_won() is True and RaceResult(kept, won, _Payouts(), {}).logic_danger_won() is True
    assert RaceResult(cancelled, won, _Payouts(), {}).danger_won() is True and RaceResult(cancelled, won, _Payouts(), {}).logic_danger_won() is None
    assert RaceResult(kept, FINISHES, _Payouts(), {}).danger_won() is False
    assert RaceResult(_forecast(), FINISHES, _Payouts(), {}).danger_won() is None
    results = [(forecast, RaceResult(forecast, won, _Payouts(), {})) for forecast in (kept, cancelled, _forecast())]
    assert "消は AI だけ 2頭（1着 2）・AI＋ロジック 1頭（1着 1）" in DayTables().build(date(2026, 11, 28), results)[1].note


def test_着順は馬番ごとに新しい行の1から3着を読む() -> None:
    columns = ("データ区分", "データ作成年月日", "開催年", "開催月日", "競馬場コード", '"開催回[第N回]"', '"開催日目[N日目]"', "レース番号", "馬番", "確定着順")
    con = duckdb.connect()
    con.execute(f"CREATE TABLE se ({', '.join(f'{name} VARCHAR' for name in columns)})")
    rows = [("2", "20261128", "2026", "1128", "05", "05", "01", "01", "05", "00"),   # 出馬表（着順なし）
            ("6", "20261128", "2026", "1128", "05", "05", "01", "01", "05", "01"),   # 速報の着順（新しい行）
            ("6", "20261128", "2026", "1128", "05", "05", "01", "01", "07", "02"),
            ("6", "20261128", "2026", "1128", "05", "05", "01", "01", "09", "04"),
            ("6", "20261128", "2026", "1128", "50", "05", "01", "01", "01", "01")]   # 中央でない競馬場
    con.executemany(f"INSERT INTO se VALUES ({', '.join('?' for _ in columns)})", rows)
    assert DayFinishes().read(con, date(2026, 11, 28)) == {RID: [(1, 5), (2, 7)]}
