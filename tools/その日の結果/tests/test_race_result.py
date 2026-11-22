"""その日の結果（1レースの精算 ``RaceResult``・着順 ``DayFinishes``・表 ``DayTables``）のテスト。値は架空。"""

from __future__ import annotations

from datetime import date

import duckdb

from その日の結果.day_finishes import DayFinishes
from その日の結果.day_tables import WAITING, DayTables
from その日の結果.race_result import RaceResult

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
    assert skipped.marks().stake == 5000 and skipped.logic().stake == 0 and skipped.logic_skipped()
    assert not RaceResult(_forecast(), FINISHES, _Payouts(), {}).logic_skipped()


def test_表は結果の届いたレースだけを合計し_届いていないレースは結果待ち() -> None:
    done, waiting = RaceResult(_forecast(), FINISHES, _Payouts(), SLOW), RaceResult(_forecast(), [], _Payouts(known=False), {})
    races, totals = DayTables().build(date(2026, 11, 28), [(_forecast(), done), (_forecast(), waiting)])
    assert races.rows[0][3:] == ["1着 5◎・2着 7○・3着 9－", "1着", "1,600円 → 4,200円（うち 100円は払戻を読めない券種）", "5,000円 → 20,000円", "見送り（展開）"]
    assert races.rows[1][3] == WAITING
    assert totals.rows == [["実際に買う買い目", 1, 1, "1,600円", "4,200円", "262.5%", "+2,600円"],
                           ["印の買い目（AI だけ）", 1, 1, "5,000円", "20,000円", "400.0%", "+15,000円"],
                           ["印の買い目（AI＋ロジック）", 0, 0, "0円", "0円", "-", "+0円"]]
    assert "結果の届いたレース 1／予想のあるレース 2" in totals.note


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
